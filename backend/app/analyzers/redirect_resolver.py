"""Segue a cadeia de redirecionamentos de uma URL ate o destino final.

Este e o UNICO modulo do projeto que faz uma requisicao de rede. Todo o resto
da ferramenta e analise estatica, e isso e uma promessa escrita na interface -
por isso esta funcao nunca e chamada sozinha: ela so roda quando a pessoa pede
explicitamente, por um endpoint separado.

O que ele resolve
-----------------
Um encurtador esconde o destino. `https://linkly.link/2zAps` pode levar ao
Google ou a uma pagina de roubo de credenciais, e a estrutura do endereco nao
responde qual dos dois - porque o endereco e o mesmo nos dois casos.

O que ele NAO resolve
---------------------
Um redirecionador pode servir destinos diferentes conforme quem pergunta: IP
de origem, user-agent, horario, ou se aquele link ja foi aberto antes. Isso se
chama *cloaking* e e padrao em phishing bem feito.

Ou seja: o resultado daqui e para onde ESTE servidor foi mandado, neste
instante. Nao e necessariamente para onde a vitima iria. A interface precisa
dizer isso - prometer mais seria o tipo de afirmacao sem lastro que a
ferramenta inteira existe para evitar.

Por que os saltos sao seguidos a mao
------------------------------------
O `httpx` segue redirecionamentos sozinho com `follow_redirects=True`. Nao
serve aqui por dois motivos: a cadeia intermediaria se perde, e - mais grave -
cada salto deixaria de passar pela verificacao de SSRF. Seguir a mao e o que
permite inspecionar antes de cada conexao.
"""

from __future__ import annotations

import ipaddress
import socket
import time
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlsplit

import httpx2 as httpx

from app.constants.network_policy import (
    ALLOWED_REDIRECT_SCHEMES,
    HOP_TIMEOUT_SECONDS,
    MAX_REDIRECT_HOPS,
    RESOLVER_USER_AGENT,
    TOTAL_TIMEOUT_SECONDS,
)


@dataclass(slots=True)
class Hop:
    """Um passo da cadeia."""

    url: str
    status_code: int | None = None
    host: str = ""


@dataclass(slots=True)
class RedirectChain:
    """Resultado de seguir uma URL ate onde der."""

    start_url: str
    hops: list[Hop] = field(default_factory=list)

    #: Onde a cadeia parou. None quando nem o primeiro salto aconteceu.
    final_url: str | None = None

    #: Verdadeiro quando a cadeia terminou num destino, e nao num limite.
    completed: bool = False

    #: Por que parou, quando nao completou. Texto para a interface exibir.
    stopped_reason: str | None = None

    @property
    def hop_count(self) -> int:
        return len(self.hops)


def _is_blocked_address(raw: str) -> bool:
    """Diz se um IP pertence a uma faixa que o servidor nao deve alcancar.

    A regra e por INCLUSAO, nao por exclusao: so passa o que for comprovadamente
    alcancavel na internet publica. Lista de faixas proibidas envelhece - toda
    faixa que alguem esquecer vira buraco - enquanto `is_global` acompanha o
    registro da IANA junto com o Python.

    Os dois sinalizadores sao necessarios, e cada um cobre o que o outro perde:

        100.64.0.1    (CGNAT)      is_private=False  is_global=False
        224.0.0.1     (multicast)  is_private=False  is_global=True

    Usar so `is_private`, que e o reflexo obvio, deixaria o CGNAT passar. Usar
    so `is_global` deixaria o multicast passar. O primeiro buraco foi
    encontrado por um teste, nao por leitura do codigo - por isso os dois
    enderecos acima estao fixados em `test_redirect_resolver.py`.
    """
    try:
        address = ipaddress.ip_address(raw)
    except ValueError:
        # Nao e um IP. Quem chama ja resolveu o nome antes, entao chegar aqui
        # significa resposta estranha do resolvedor: tratar como bloqueado.
        return True

    return not address.is_global or address.is_multicast


def _resolves_to_blocked_address(host: str) -> bool:
    """Resolve o nome e diz se QUALQUER endereco dele e proibido.

    Qualquer, e nao apenas o primeiro: um nome pode apontar para varios
    enderecos, e basta um interno para o ataque funcionar.

    Limitacao conhecida, registrada de proposito: entre esta verificacao e a
    conexao real existe uma janela em que o DNS pode responder outra coisa -
    o ataque chamado *DNS rebinding*. Fechar isso exigiria conectar direto ao
    IP ja verificado, com o nome no cabecalho Host, o que quebra TLS sem
    trabalho adicional. Para o risco desta ferramenta, verificar cada salto e
    a mitigacao proporcional; o buraco fica documentado em vez de escondido.
    """
    try:
        resolved = socket.getaddrinfo(host, None)
    except (socket.gaierror, UnicodeError, ValueError):
        # Nome que nao resolve nao chega a lugar nenhum. Bloquear aqui evita
        # que o httpx tente de novo e gaste o tempo da cadeia.
        return True

    return any(_is_blocked_address(info[4][0]) for info in resolved)


def _check_url(url: str) -> str | None:
    """Devolve o motivo para NAO seguir esta URL, ou None quando pode."""
    try:
        split = urlsplit(url)
    except ValueError:
        return "malformed"

    if split.scheme.lower() not in ALLOWED_REDIRECT_SCHEMES:
        return "scheme_not_allowed"

    if not split.hostname:
        return "no_host"

    if _resolves_to_blocked_address(split.hostname):
        return "internal_address"

    return None


def resolve_redirects(url: str) -> RedirectChain:
    """Segue `url` ate o destino final, um salto por vez.

    Nunca levanta excecao: a entrada vem de quem esta sendo investigado, e
    qualquer falha de rede vira `stopped_reason` para a interface explicar.
    """
    chain = RedirectChain(start_url=url)
    started_at = time.monotonic()

    current = url
    seen: set[str] = set()

    timeout = httpx.Timeout(HOP_TIMEOUT_SECONDS)
    headers = {"User-Agent": RESOLVER_USER_AGENT, "Accept": "*/*"}

    try:
        # `follow_redirects=False` e o ponto central: cada salto volta para
        # este laco, onde passa pela verificacao antes da proxima conexao.
        with httpx.Client(
            follow_redirects=False,
            timeout=timeout,
            headers=headers,
            # Cookie de um salto nao deve ser devolvido no proximo: a cadeia
            # pode atravessar dominios de donos diferentes.
            cookies=None,
        ) as client:
            while True:
                if chain.hop_count >= MAX_REDIRECT_HOPS:
                    chain.stopped_reason = "too_many_hops"
                    break

                if time.monotonic() - started_at > TOTAL_TIMEOUT_SECONDS:
                    chain.stopped_reason = "timeout"
                    break

                if current in seen:
                    chain.stopped_reason = "loop"
                    break

                seen.add(current)

                blocked = _check_url(current)

                if blocked is not None:
                    chain.stopped_reason = blocked
                    break

                host = urlsplit(current).hostname or ""
                hop = Hop(url=current, host=host)

                try:
                    # HEAD primeiro: pede so os cabecalhos. O corpo de uma
                    # pagina hostil nao interessa e nao deve ser baixado.
                    response = client.head(current)

                    # Nem todo servidor implementa HEAD. Quando ele recusa, um
                    # GET em modo fluxo resolve - e e fechado antes de ler o
                    # corpo, entao continua sem baixar conteudo.
                    if response.status_code in (405, 501):
                        with client.stream("GET", current) as streamed:
                            response = streamed
                except httpx.HTTPError as error:
                    hop.status_code = None
                    chain.hops.append(hop)
                    chain.stopped_reason = f"request_failed:{type(error).__name__}"
                    break

                hop.status_code = response.status_code
                chain.hops.append(hop)

                location = response.headers.get("location")

                if not (300 <= response.status_code < 400) or not location:
                    chain.final_url = current
                    chain.completed = True
                    break

                # `Location` pode vir relativo. `urljoin` resolve contra a URL
                # atual, que e exatamente o que o navegador faria.
                current = urljoin(current, location)
    except Exception as error:  # noqa: BLE001 - fronteira com a rede
        # Rede e entrada hostil: nenhuma falha aqui pode derrubar a API.
        chain.stopped_reason = f"failed:{type(error).__name__}"

    return chain
