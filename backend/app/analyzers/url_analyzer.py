"""Analise heuristica de URLs.

Uma URL nao e um texto solto: e um documento estruturado, e cada parte dele
pode ser examinada.

    https://user:senha@xn--80ak6aa92e.banco.com.br.phish.tk:8443/login/nota.pdf.exe?r=aHR0cDov
    └─esq. └─credenciais └─punycode   └──────── host ────────┘ └porta └─── caminho ───┘ └query

Dessa unica linha saem varios indicadores - todos verificaveis localmente,
**sem nenhuma requisicao de rede**.

Por que nada e consultado online
--------------------------------
Infraestrutura de phishing registra cada acesso. Resolver o DNS, buscar o
certificado ou abrir a pagina avisa a quem montou aquilo que esta sendo
investigado - e a resposta costuma ser derrubar o servidor ou passar a servir
conteudo inocente para o IP do analista.

Por isso tudo aqui e estrutural. O que exigir rede fica de fora, por decisao,
nao por limitacao.

E o aviso de sempre: **nada disto identifica uma URL como maliciosa.** Sao
caracteristicas incomuns. O valor esta na combinacao.
"""

from __future__ import annotations

import ipaddress
import re
import unicodedata
from dataclasses import dataclass, field
from urllib.parse import unquote, urlsplit

from app.constants.url_patterns import (
    DANGEROUS_SCHEMES,
    DECOY_EXTENSIONS,
    EXECUTABLE_PATH_EXTENSIONS,
    MAX_PERCENT_ENCODINGS,
    MAX_SHORTENER_HOST_LENGTH,
    MAX_SHORTENER_PATH_LENGTH,
    MAX_SUBDOMAIN_LABELS,
    MAX_URL_LENGTH,
    MIN_SHORTENER_PATH_LENGTH,
    MULTIPART_SUFFIXES,
    RISKY_TLDS,
    STANDARD_PORTS,
    URL_SHORTENERS,
)

# Prefixo que identifica rotulos codificados em punycode.
#
# Punycode representa caracteres nao-ASCII usando apenas ASCII, o que permite
# dominios em arabe, chines ou com acentuacao. E legitimo e amplamente usado -
# e tambem o que torna possivel registrar um dominio visualmente identico a uma
# marca conhecida, trocando uma letra latina por outra de aparencia igual.
PUNYCODE_PREFIX = "xn--"

# Reconhece algo com cara de dominio dentro de um texto qualquer.
DOMAIN_IN_TEXT_PATTERN = re.compile(
    r"\b(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z]{2,}\b",
    re.IGNORECASE,
)

PERCENT_ENCODING_PATTERN = re.compile(r"%[0-9A-Fa-f]{2}")

# Host escrito como numero em vez de nome ou IP decimal: `0x7f000001`,
# `2130706433`, `0177.0.0.1`. O navegador resolve todos para o mesmo endereco,
# mas nenhum deles parece um endereco para quem le.
NUMERIC_HOST_PATTERN = re.compile(r"^(?:0[xX][0-9a-fA-F]+|\d{8,10}|0\d+(?:\.0\d+)*)$")


@dataclass(frozen=True)
class UrlParts:
    """A URL dissecada nas suas partes."""

    scheme: str = ""
    username: str | None = None
    password: str | None = None
    host: str = ""
    unicode_host: str = ""
    port: int | None = None
    path: str = ""
    query: str = ""
    fragment: str = ""

    registrable_domain: str = ""
    subdomains: tuple[str, ...] = ()
    tld: str = ""


@dataclass(frozen=True)
class UrlAnalysis:
    """O que se observou sobre uma URL.

    Cada campo booleano e uma caracteristica encontrada, nunca um veredito.
    A traducao disso em pontuacao e trabalho do Risk Engine.
    """

    url: str
    parts: UrlParts = field(default_factory=UrlParts)

    dangerous_scheme: bool = False
    insecure_scheme: bool = False
    has_credentials: bool = False
    ip_address_host: bool = False
    private_host: bool = False
    numeric_host: bool = False
    punycode_domain: bool = False
    mixed_scripts: bool = False
    scripts_found: tuple[str, ...] = ()
    risky_tld: bool = False
    url_shortener: bool = False
    # Tem a FORMA de um redirecionador, mesmo sem estar na lista de conhecidos.
    redirector_shape: bool = False
    excessive_subdomains: bool = False
    non_standard_port: bool = False
    executable_path: bool = False
    double_extension: bool = False
    excessive_length: bool = False
    heavy_encoding: bool = False

    error: str | None = None


def analyze_url(raw: str) -> UrlAnalysis:
    """Disseca uma URL e aponta as caracteristicas incomuns.

    Qualquer falha de parsing vira o campo `error`, nunca excecao: a entrada
    vem de quem esta sendo investigado e pode ser qualquer coisa.
    """
    url = raw.strip()

    if not url:
        return UrlAnalysis(url=raw, error="Empty URL")

    try:
        split = urlsplit(url)
    except ValueError as error:
        return UrlAnalysis(url=raw, error=f"Could not parse URL: {type(error).__name__}")

    scheme = split.scheme.lower()

    # Esquemas que carregam conteudo em vez de apontar para um endereco nao
    # tem host, caminho nem dominio - a analise estrutural para por aqui.
    if scheme in DANGEROUS_SCHEMES:
        return UrlAnalysis(
            url=url,
            parts=UrlParts(scheme=scheme),
            dangerous_scheme=True,
            excessive_length=len(url) > MAX_URL_LENGTH,
        )

    try:
        host = (split.hostname or "").lower()
        port = split.port
    except ValueError:
        # Porta invalida, colchetes desbalanceados em IPv6, e afins.
        return UrlAnalysis(url=url, parts=UrlParts(scheme=scheme), error="Malformed authority")

    unicode_host = _decode_punycode(host)
    registrable, subdomains, tld = _split_domain(host)

    ip_host, private = _classify_ip_host(host)
    scripts = _scripts_in(unicode_host)

    path = split.path

    return UrlAnalysis(
        url=url,
        parts=UrlParts(
            scheme=scheme,
            username=split.username,
            password=split.password,
            host=host,
            unicode_host=unicode_host,
            port=port,
            path=path,
            query=split.query,
            fragment=split.fragment,
            registrable_domain=registrable,
            subdomains=subdomains,
            tld=tld,
        ),
        insecure_scheme=scheme == "http" and not private,
        has_credentials=bool(split.username or split.password),
        ip_address_host=ip_host and not private,
        private_host=private,
        numeric_host=bool(NUMERIC_HOST_PATTERN.match(host)),
        punycode_domain=any(label.startswith(PUNYCODE_PREFIX) for label in host.split(".")),
        mixed_scripts=len(scripts) > 1,
        scripts_found=scripts,
        risky_tld=tld in RISKY_TLDS,
        url_shortener=registrable in URL_SHORTENERS,
        # A forma so e relatada quando o dominio NAO esta na lista. Nos dois
        # casos o problema e o mesmo - destino escondido - e dizer duas vezes
        # inflaria a nota de um unico achado.
        redirector_shape=(
            registrable not in URL_SHORTENERS
            and not private
            and _looks_like_redirector(host, subdomains, path, split.query, split.fragment)
        ),
        excessive_subdomains=len(subdomains) > MAX_SUBDOMAIN_LABELS,
        # Porta incomum so vira sinal em host publico. Em rede interna ela e
        # o dia a dia - servidor de desenvolvimento, painel administrativo,
        # servico interno - e marca-la encheria o relatorio de ruido.
        non_standard_port=_is_non_standard_port(scheme, port) and not private,
        executable_path=_has_executable_extension(path),
        double_extension=_has_double_extension(path),
        excessive_length=len(url) > MAX_URL_LENGTH,
        heavy_encoding=len(PERCENT_ENCODING_PATTERN.findall(url)) > MAX_PERCENT_ENCODINGS,
    )


# ---------------------------------------------------------------------------
# Host
# ---------------------------------------------------------------------------


def _decode_punycode(host: str) -> str:
    """Converte um host em punycode para a forma que o navegador exibe.

    E essa forma que importa para a deteccao de homografo: `xn--pple-43d.com`
    nao parece nada, mas `аpple.com` - com "а" cirilico - e indistinguivel de
    `apple.com` a olho nu.
    """
    if PUNYCODE_PREFIX not in host:
        return host

    try:
        return host.encode("ascii").decode("idna")
    except (UnicodeError, UnicodeDecodeError):
        # Punycode malformado. Devolve a forma original em vez de falhar.
        return host


def _scripts_in(host: str) -> tuple[str, ...]:
    """Quais sistemas de escrita aparecem no host.

    Um dominio legitimo usa um alfabeto so. A mistura de latino com cirilico
    ou grego e a assinatura do ataque homografo, onde uma letra e trocada por
    outra de aparencia identica em outro alfabeto.

    Digitos e pontuacao sao ignorados: eles aparecem em qualquer alfabeto e
    marcariam todo dominio com numero no nome.
    """
    scripts: set[str] = set()

    for character in host:
        if not character.isalpha():
            continue

        try:
            name = unicodedata.name(character)
        except ValueError:
            continue

        # O nome Unicode de uma letra comeca pelo sistema de escrita:
        # "LATIN SMALL LETTER A", "CYRILLIC SMALL LETTER A".
        scripts.add(name.split(" ", 1)[0])

    return tuple(sorted(scripts))


# Faixas de rede interna, verificadas explicitamente.
#
# NAO usamos `is_private` do modulo ipaddress: ele e mais amplo do que o nome
# sugere e inclui as faixas reservadas para DOCUMENTACAO (203.0.113.0/24,
# 2001:db8::/32) junto com as redes locais de verdade.
#
# A diferenca importa: um endereco de documentacao numa URL recebida por
# e-mail e tao estranho quanto qualquer outro IP no lugar do dominio, enquanto
# `192.168.0.10` e o dia a dia de qualquer rede interna.
INTERNAL_NETWORKS = (
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("fc00::/7"),
)


# Sufixos reservados a nomes que nunca saem da rede local.
#
# `.local` e usado por mDNS, `.internal` e convencao em nuvem privada, e
# `.test` e `.invalid` sao reservados pela RFC 2606 justamente para nao
# existirem na internet publica.
INTERNAL_SUFFIXES = (".local", ".internal", ".home.arpa", ".test", ".invalid")


def _is_internal_hostname(host: str) -> bool:
    """Diz se o NOME do host indica rede interna.

    Complementa a verificacao por endereco IP. `localhost` e o host interno
    mais comum que existe e nao e um IP - sem este caminho, a propria
    documentacao desta API pontuaria por HTTP sem TLS e porta fora do padrao.

    Um nome sem ponto nenhum tambem e interno por natureza: `intranet` ou
    `servidor-arquivos` so resolvem dentro de uma rede.
    """
    return host == "localhost" or host.endswith(INTERNAL_SUFFIXES) or "." not in host


def _classify_ip_host(host: str) -> tuple[bool, bool]:
    """Diz se o host e um endereco IP e se ele e de rede interna.

    A distincao importa. Um IP publico no lugar do dominio evita registro e
    verificacao de reputacao - e incomum em conteudo destinado a pessoas. Ja
    `127.0.0.1` ou `192.168.0.10` sao trafego interno normal, e marca-los
    encheria o relatorio de ruido.
    """
    try:
        address = ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        return False, _is_internal_hostname(host)

    same_family = (network for network in INTERNAL_NETWORKS if network.version == address.version)

    internal = (
        address.is_loopback
        or address.is_link_local
        or any(address in network for network in same_family)
    )

    return True, internal


def _split_domain(host: str) -> tuple[str, tuple[str, ...], str]:
    """Separa o host em subdominios, dominio registravel e TLD.

    Usa a lista de sufixos compostos para que `empresa.com.br` seja tratado
    como um dominio sem subdominio - e nao como `empresa` sob `com.br`.
    """
    if not host or _classify_ip_host(host)[0]:
        return host, (), ""

    labels = host.split(".")

    if len(labels) < 2:
        return host, (), ""

    suffix_labels = 2 if ".".join(labels[-2:]) in MULTIPART_SUFFIXES else 1

    # O dominio registravel e o sufixo mais o rotulo imediatamente antes dele.
    registrable_start = max(0, len(labels) - suffix_labels - 1)

    return (
        ".".join(labels[registrable_start:]),
        tuple(labels[:registrable_start]),
        labels[-1],
    )


def _is_non_standard_port(scheme: str, port: int | None) -> bool:
    """Diz se a porta difere da padrao do esquema.

    Porta ausente significa a padrao, entao nao e divergencia.
    """
    if port is None:
        return False

    return STANDARD_PORTS.get(scheme) != port


# ---------------------------------------------------------------------------
# Caminho
# ---------------------------------------------------------------------------


def _path_extensions(path: str) -> list[str]:
    """Extensoes do ultimo segmento do caminho, em minusculas.

    O caminho e decodificado antes: `%2Eexe` precisa ser lido como `.exe`,
    caso contrario a verificacao e contornada com uma unica substituicao.
    """
    decoded = unquote(path)
    name = decoded.rstrip("/").rsplit("/", 1)[-1]

    if "." not in name:
        return []

    return [f".{part.lower()}" for part in name.split(".")[1:]]


def _has_executable_extension(path: str) -> bool:
    extensions = _path_extensions(path)

    return bool(extensions) and extensions[-1] in EXECUTABLE_PATH_EXTENSIONS


def _has_double_extension(path: str) -> bool:
    """Diz se o caminho termina em extensao inofensiva seguida de executavel.

    `fatura.pdf.exe` aparece como "fatura.pdf" em sistemas configurados para
    esconder a extensao final - que e o padrao do Windows.
    """
    extensions = _path_extensions(path)

    if len(extensions) < 2:
        return False

    return extensions[-2] in DECOY_EXTENSIONS and extensions[-1] in EXECUTABLE_PATH_EXTENSIONS


def _looks_like_redirector(
    host: str,
    subdomains: list[str],
    path: str,
    query: str,
    fragment: str,
) -> bool:
    """Diz se a URL tem a FORMA de um redirecionador, sem consultar lista.

    A lista de encurtadores conhecidos so pega o que alguem ja pensou em
    listar, e ela esta sempre desatualizada - existem centenas de servicos e
    qualquer um hospeda o proprio. Esta funcao olha a estrutura.

    Exige os tres sinais juntos. Cada um sozinho aparece em URL legitima; os
    tres ao mesmo tempo sao raros fora de um redirecionador, porque site de
    verdade quase sempre tem caminho descritivo, mais de um nivel, ou
    parametros.

    O identificador precisa misturar letras e digitos, ou misturar
    maiusculas e minusculas. Sem isso, `exemplo.com/sobre` seria marcado -
    e "sobre" e uma palavra, nao um identificador gerado.
    """
    if query or fragment or subdomains:
        return False

    if len(host) > MAX_SHORTENER_HOST_LENGTH:
        return False

    segments = [segment for segment in path.split("/") if segment]

    if len(segments) != 1:
        return False

    identifier = segments[0]

    if not MIN_SHORTENER_PATH_LENGTH <= len(identifier) <= MAX_SHORTENER_PATH_LENGTH:
        return False

    if not identifier.isalnum():
        return False

    mixes_digits = any(c.isdigit() for c in identifier) and any(c.isalpha() for c in identifier)
    mixes_case = identifier != identifier.lower() and identifier != identifier.upper()

    return mixes_digits or mixes_case


# ---------------------------------------------------------------------------
# Funcoes usadas pela analise de e-mail e de arquivo
# ---------------------------------------------------------------------------


def extract_host(url: str) -> str | None:
    """Devolve o host de uma URL, ou None quando nao da para determinar."""
    try:
        host = urlsplit(url).hostname
    except ValueError:
        return None

    return host or None


def has_ip_address_host(url: str) -> bool:
    """Diz se a URL aponta para um endereco IP publico."""
    host = extract_host(url)

    if host is None:
        return False

    is_ip, private = _classify_ip_host(host)

    return is_ip and not private


def has_punycode_domain(url: str) -> bool:
    """Diz se alguma parte do dominio esta codificada em punycode."""
    host = extract_host(url)

    if host is None:
        return False

    return any(label.startswith(PUNYCODE_PREFIX) for label in host.split("."))


def is_misleading_link(url: str, display_text: str) -> bool:
    """Diz se o texto exibido de um link aponta para um destino diferente.

    A tecnica classica de phishing num e-mail HTML:

        <a href="http://evil.example/x">www.banco.com.br</a>

    O usuario le `www.banco.com.br` e clica para `evil.example`. Nem o texto
    nem a URL, isolados, revelam o problema.

    Se o texto nao contem nada parecido com um dominio - "Clique aqui" - nao
    ha o que comparar. Quando contem, o link so e marcado se o destino **nao
    terminar** com o dominio exibido, o que evita marcar subdominio legitimo.
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
    """Filtra as URLs que apontam para endereco IP publico."""
    return [url for url in urls if has_ip_address_host(url)]


def find_punycode_urls(urls: list[str]) -> list[str]:
    """Filtra as URLs com dominio em punycode."""
    return [url for url in urls if has_punycode_domain(url)]
