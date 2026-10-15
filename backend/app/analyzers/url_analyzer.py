"""Analise heuristica de URLs encontradas numa evidencia.

Esta e a versao minima do modulo: apenas o que o Risk Engine precisa agora.
As heuristicas restantes previstas na especificacao - subdominios em excesso,
URLs muito longas, presenca de `@`, encurtadores conhecidos, HTTP sem TLS -
chegam junto com a analise de e-mail, onde fazem mais diferenca.

Um aviso que vale para o modulo inteiro: **uma URL heuristicamente suspeita
nao e uma URL maliciosa.** Tudo aqui aponta caracteristicas incomuns, nao
intencao.
"""

from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlsplit

# Reconhece algo com cara de dominio dentro de um texto qualquer.
#
# Exige pelo menos um ponto e um sufixo de duas letras ou mais, para nao casar
# com palavras comuns. Nao e uma validacao de dominio - e uma pista de que o
# texto esta se apresentando como um endereco.
DOMAIN_IN_TEXT_PATTERN = re.compile(
    r"\b(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z]{2,}\b",
    re.IGNORECASE,
)

# Prefixo que identifica dominios codificados em punycode.
#
# Punycode representa caracteres nao-ASCII usando apenas ASCII, o que permite
# dominios em arabe, chines ou com acentuacao. E um mecanismo legitimo e
# amplamente usado - e tambem o que torna possivel registrar um dominio
# visualmente identico a uma marca conhecida, trocando uma letra latina por
# outra de aparencia igual em outro alfabeto.
PUNYCODE_PREFIX = "xn--"


def extract_host(url: str) -> str | None:
    """Devolve o host de uma URL, ou None quando nao da para determinar.

    URLs vem de dentro de arquivos nao confiaveis e frequentemente estao
    truncadas ou malformadas. Qualquer falha de parsing vira None, nunca
    excecao: uma URL quebrada no meio de um binario nao pode derrubar a
    analise.
    """
    try:
        host = urlsplit(url).hostname
    except ValueError:
        # urlsplit levanta ValueError em casos como porta invalida ou
        # colchetes desbalanceados em endereco IPv6.
        return None

    return host or None


def has_ip_address_host(url: str) -> bool:
    """Diz se a URL aponta para um endereco IP em vez de um dominio.

    Nao e prova de nada - servicos internos e dispositivos de rede usam IP o
    tempo todo. Mas conteudo destinado a pessoas quase sempre usa nome de
    dominio, e usar IP evita registro e verificacao de reputacao.
    """
    host = extract_host(url)

    if host is None:
        return False

    try:
        ipaddress.ip_address(host)
    except ValueError:
        return False

    return True


def has_punycode_domain(url: str) -> bool:
    """Diz se alguma parte do dominio esta codificada em punycode.

    A verificacao e por rotulo (`a.xn--80ak6aa92e.com`), e nao por "contem a
    string": assim `meu-xn--site.com`, que apenas contem esses caracteres no
    meio de uma palavra, nao e marcado.
    """
    host = extract_host(url)

    if host is None:
        return False

    return any(label.startswith(PUNYCODE_PREFIX) for label in host.split("."))


def is_misleading_link(url: str, display_text: str) -> bool:
    """Diz se o texto exibido de um link aponta para um destino diferente.

    A tecnica classica de phishing num e-mail HTML:

        <a href="http://evil.example/x">www.banco.com.br</a>

    O usuario le `www.banco.com.br` e clica para `evil.example`. Nem o texto
    nem a URL, isolados, revelam o problema - e preciso comparar os dois.

    Como a comparacao e feita
    -------------------------
    Se o texto exibido nao contem nada parecido com um dominio - "Clique
    aqui", "Ver fatura" - nao ha nada a comparar, e o link nao e marcado.

    Quando contem, o link so e considerado enganoso se o destino real **nao
    terminar** com o dominio exibido. Essa regra evita o falso positivo mais
    comum:

        exibido `banco.com.br`, destino `login.banco.com.br`   -> normal
        exibido `www.banco.com.br`, destino `evil.example`     -> enganoso

    Limitacao conhecida e aceita: sem uma lista de sufixos publicos, a
    comparacao e por sufixo de hostname. Um dominio hostil chamado
    `evil-banco.com.br` nao termina em `banco.com.br` e seria marcado
    corretamente, mas `banco.com.br.evil.example` tambem nao termina nele - e
    tambem seria marcado. Os dois casos sao de fato suspeitos, entao o erro
    cai para o lado seguro.
    """
    destination = extract_host(url)

    if destination is None:
        return False

    match = DOMAIN_IN_TEXT_PATTERN.search(display_text)

    if match is None:
        return False

    displayed = match.group(0).lower().removeprefix("www.")
    destination = destination.removeprefix("www.")

    return not destination.endswith(displayed)


def find_ip_address_urls(urls: list[str]) -> list[str]:
    """Filtra as URLs que apontam para endereco IP."""
    return [url for url in urls if has_ip_address_host(url)]


def find_punycode_urls(urls: list[str]) -> list[str]:
    """Filtra as URLs com dominio em punycode."""
    return [url for url in urls if has_punycode_domain(url)]
