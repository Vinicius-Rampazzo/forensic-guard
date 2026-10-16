"""Analise forense de mensagens de e-mail (.eml).

O que um e-mail realmente e
---------------------------
Texto. Um arquivo `.eml` e a mensagem exatamente como trafegou: uma lista de
cabecalhos, uma linha em branco, e o corpo.

E aqui mora o fato mais importante da analise de e-mail: **quase todo cabecalho
e escrito por quem envia.** `From`, `Reply-To`, `Subject`, `Date` - nada disso
e verificado pelo protocolo. Falsificar um remetente e trivial, e o SMTP foi
desenhado numa epoca em que isso nao era problema.

O que da para confiar
---------------------
Os cabecalhos `Received` e `Authentication-Results` sao acrescentados pelos
servidores que a mensagem atravessou, de baixo para cima. Eles nao vem do
remetente, e por isso valem mais que o resto.

O `Authentication-Results` em especial carrega o veredito de SPF, DKIM e DMARC
emitido pelo servidor que recebeu a mensagem. Nos apenas lemos esse veredito:
revalidar por DNS exigiria rede, quebraria o principio local-first, e avaliaria
um e-mail antigo com os registros de hoje - que podem ter mudado.

Nenhum conteudo e executado, renderizado ou buscado na rede.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from email import message_from_binary_file
from email.header import decode_header, make_header
from email.message import Message
from email.utils import parseaddr
from html.parser import HTMLParser
from pathlib import Path

from app.analyzers.url_analyzer import is_misleading_link

# Limites de analise recursiva, conforme a especificacao.
#
# Sem eles, um e-mail que contem um e-mail que contem outro e-mail poderia
# descer indefinidamente - uma bomba de aninhamento. E vinte anexos ja sao
# muito mais do que qualquer mensagem legitima carrega.
MAX_ATTACHMENTS = 20
MAX_ATTACHMENT_DEPTH = 2

# Teto de partes MIME percorridas. Uma mensagem pode ser montada com milhares
# de partes vazias so para consumir tempo de processamento.
MAX_MIME_PARTS = 500

# Tamanho maximo de um anexo mantido em memoria para analise.
MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024

# Tamanho maximo de um arquivo .eml analisado.
#
# Este e o UNICO ponto do projeto que precisa do arquivo inteiro em memoria:
# o parser constroi a arvore MIME completa antes de devolver qualquer coisa,
# e nao existe forma de percorrer as partes sem monta-la.
#
# Por isso o teto aqui e proprio, e muito menor que o limite geral de upload.
# Sem ele, um `.eml` do tamanho do limite de upload consumiria essa memoria
# toda de uma vez - e duas analises simultaneas derrubariam o servico.
#
# 64 MB cobre com folga qualquer mensagem real: provedores recusam anexos bem
# antes disso, e um e-mail maior que a caixa de entrada inteira de muita gente
# e, por si so, anomalo.
MAX_EMAIL_BYTES = 64 * 1024 * 1024

# Quantas URLs sao reportadas. Um corpo HTML pode ter centenas de links.
MAX_URLS = 200

# Resultados de autenticacao procurados no Authentication-Results.
# O formato e `metodo=resultado`, com o resultado em minusculas.
AUTH_RESULT_PATTERN = re.compile(r"\b(spf|dkim|dmarc)\s*=\s*([a-z]+)", re.IGNORECASE)

# Resultados que indicam falha de verificacao. `none` fica de fora de
# proposito: significa que o dominio nao publicou a politica, o que e omissao
# do dominio e nao sinal de falsificacao.
FAILURE_RESULTS = frozenset({"fail", "softfail", "permerror", "temperror", "policy"})

URL_IN_TEXT_PATTERN = re.compile(r"\b(?:https?|ftp)://[^\s\"'<>()\[\]{}]{4,}", re.IGNORECASE)

# Cabecalhos principais exibidos no relatorio, na ordem em que fazem sentido
# para quem le.
REPORTED_HEADERS = (
    "From",
    "To",
    "Cc",
    "Subject",
    "Date",
    "Message-ID",
    "Reply-To",
    "Return-Path",
)


@dataclass(frozen=True)
class AuthenticationResults:
    """Veredito de SPF, DKIM e DMARC lido dos cabecalhos.

    Cada campo e None quando o resultado nao foi informado - o que acontece
    sempre que a mensagem nunca passou por um servidor que verifica, como num
    `.eml` exportado antes da entrega.
    """

    spf: str | None = None
    dkim: str | None = None
    dmarc: str | None = None
    raw: str | None = None

    @property
    def spf_failed(self) -> bool:
        return self.spf is not None and self.spf.lower() in FAILURE_RESULTS

    @property
    def dkim_failed(self) -> bool:
        return self.dkim is not None and self.dkim.lower() in FAILURE_RESULTS

    @property
    def dmarc_failed(self) -> bool:
        return self.dmarc is not None and self.dmarc.lower() in FAILURE_RESULTS


@dataclass(frozen=True)
class EmailLink:
    """Um link do corpo HTML, com o texto que o usuario enxerga."""

    url: str
    display_text: str
    misleading: bool


@dataclass(frozen=True)
class EmailAttachment:
    """Um anexo extraido da mensagem.

    O conteudo fica em memoria porque o servico precisa grava-lo num
    temporario para analisa-lo. O tamanho e limitado por isso.
    """

    filename: str
    declared_content_type: str
    size: int
    payload: bytes = field(repr=False)


@dataclass(frozen=True)
class EmailAnalysis:
    """O que se conseguiu observar sobre a mensagem."""

    headers: dict[str, str] = field(default_factory=dict)
    from_address: str | None = None
    from_domain: str | None = None
    reply_to: str | None = None
    reply_to_domain: str | None = None
    return_path: str | None = None
    return_path_domain: str | None = None

    received_chain: tuple[str, ...] = ()
    authentication: AuthenticationResults = field(default_factory=AuthenticationResults)

    reply_to_mismatch: bool = False
    return_path_mismatch: bool = False

    has_text_body: bool = False
    has_html_body: bool = False
    urls: tuple[str, ...] = ()
    links: tuple[EmailLink, ...] = ()

    attachments: tuple[EmailAttachment, ...] = ()
    attachments_truncated: bool = False

    error: str | None = None

    @property
    def misleading_links(self) -> tuple[EmailLink, ...]:
        return tuple(link for link in self.links if link.misleading)


def analyze_email(path: Path) -> EmailAnalysis:
    """Analisa um arquivo de e-mail.

    Qualquer falha de parsing vira o campo `error`, nunca excecao: mensagens
    vem de origem nao confiavel e podem estar truncadas, com codificacao
    quebrada ou deliberadamente malformadas.
    """
    try:
        size = path.stat().st_size

        # Verificado ANTES de abrir: depois que o parser comeca, a memoria ja
        # foi comprometida. O numero exato entra na mensagem para que quem le
        # saiba o que aconteceu, em vez de receber uma recusa sem explicacao.
        if size > MAX_EMAIL_BYTES:
            return EmailAnalysis(
                error=(
                    f"Email is {size} bytes, above the {MAX_EMAIL_BYTES} byte "
                    "limit for message parsing. Parsing requires the whole "
                    "message in memory, so this limit is lower than the "
                    "general upload limit."
                )
            )

        with path.open("rb") as stream:
            message = message_from_binary_file(stream)

        return _analyze_message(message)
    except Exception as error:  # noqa: BLE001 - parser sobre entrada hostil
        return EmailAnalysis(error=f"Could not parse email: {type(error).__name__}")


def _analyze_message(message: Message) -> EmailAnalysis:
    """Extrai tudo o que interessa de uma mensagem ja parseada."""
    headers = {
        name: _decoded_header(message.get(name))
        for name in REPORTED_HEADERS
        if message.get(name) is not None
    }

    from_address, from_domain = _address_and_domain(message.get("From"))
    reply_to, reply_to_domain = _address_and_domain(message.get("Reply-To"))
    return_path, return_path_domain = _address_and_domain(message.get("Return-Path"))

    text_body, html_body, attachments, truncated = _walk_parts(message)

    links = _extract_links(html_body) if html_body else ()
    urls = _collect_urls(text_body, html_body, links)

    return EmailAnalysis(
        headers=headers,
        from_address=from_address,
        from_domain=from_domain,
        reply_to=reply_to,
        reply_to_domain=reply_to_domain,
        return_path=return_path,
        return_path_domain=return_path_domain,
        received_chain=tuple(
            _decoded_header(value) for value in message.get_all("Received", [])
        ),
        authentication=_parse_authentication(message),
        reply_to_mismatch=_domains_differ(from_domain, reply_to_domain),
        return_path_mismatch=_domains_differ(from_domain, return_path_domain),
        has_text_body=bool(text_body),
        has_html_body=bool(html_body),
        urls=urls,
        links=links,
        attachments=attachments,
        attachments_truncated=truncated,
    )


# ---------------------------------------------------------------------------
# Cabecalhos
# ---------------------------------------------------------------------------


def _decoded_header(raw: str | None) -> str:
    """Decodifica um cabecalho que pode estar codificado em MIME.

    Assuntos com acentuacao trafegam como `=?utf-8?B?...?=`. Sem decodificar,
    o relatorio exibiria o codigo em vez do texto.
    """
    if raw is None:
        return ""

    try:
        return str(make_header(decode_header(raw))).strip()
    except Exception:  # noqa: BLE001 - cabecalho malformado nao e erro fatal
        return str(raw).strip()


def _address_and_domain(raw: str | None) -> tuple[str | None, str | None]:
    """Separa o endereco e o dominio de um cabecalho de remetente.

    `parseaddr` lida com os varios formatos aceitos pela RFC:
    `Nome <a@b.com>`, `<a@b.com>` e `a@b.com`.
    """
    if not raw:
        return None, None

    _, address = parseaddr(_decoded_header(raw))

    if not address or "@" not in address:
        return None, None

    domain = address.rsplit("@", 1)[1].strip().lower()

    return address, domain or None


def _domains_differ(first: str | None, second: str | None) -> bool:
    """Diz se dois dominios sao diferentes, ignorando o prefixo `www.`.

    Devolve False quando qualquer um deles falta: ausencia de cabecalho nao e
    contradicao.
    """
    if not first or not second:
        return False

    return first.removeprefix("www.") != second.removeprefix("www.")


def _parse_authentication(message: Message) -> AuthenticationResults:
    """Le o veredito de SPF, DKIM e DMARC dos cabecalhos.

    Pode haver varios `Authentication-Results`, um por servidor que verificou.
    Percorremos todos e guardamos o primeiro resultado encontrado de cada
    metodo - que e o do servidor mais proximo do destinatario, porque os
    cabecalhos sao empilhados de cima para baixo.

    O `Received-SPF` entra como fonte alternativa: alguns servidores gravam
    apenas ele.
    """
    sources = list(message.get_all("Authentication-Results", []))
    raw = "; ".join(str(value) for value in sources) if sources else None

    found: dict[str, str] = {}

    for value in sources:
        for method, result in AUTH_RESULT_PATTERN.findall(str(value)):
            found.setdefault(method.lower(), result.lower())

    if "spf" not in found:
        for value in message.get_all("Received-SPF", []):
            # O formato e `Pass (...)` ou `Fail (...)`: a primeira palavra.
            first_word = str(value).strip().split(maxsplit=1)
            if first_word:
                found["spf"] = first_word[0].lower().rstrip(";")
                break

    return AuthenticationResults(
        spf=found.get("spf"),
        dkim=found.get("dkim"),
        dmarc=found.get("dmarc"),
        raw=raw,
    )


# ---------------------------------------------------------------------------
# Corpo e anexos
# ---------------------------------------------------------------------------


def _walk_parts(
    message: Message,
) -> tuple[str, str, tuple[EmailAttachment, ...], bool]:
    """Percorre as partes MIME separando corpo de anexos.

    Uma mensagem e uma arvore: `multipart/mixed` contendo `multipart/
    alternative` contendo as versoes texto e HTML, mais os anexos ao lado.

    O contador de partes existe por seguranca: uma mensagem pode ser montada
    com milhares de partes vazias apenas para consumir tempo.
    """
    text_body = ""
    html_body = ""
    attachments: list[EmailAttachment] = []
    truncated = False
    parts_seen = 0

    for part in message.walk():
        parts_seen += 1

        if parts_seen > MAX_MIME_PARTS:
            truncated = True
            break

        if part.get_content_maintype() == "multipart":
            continue

        if _is_attachment(part):
            if len(attachments) >= MAX_ATTACHMENTS:
                truncated = True
                continue

            attachment = _build_attachment(part)

            if attachment is not None:
                attachments.append(attachment)

            continue

        content = _decoded_text(part)

        if part.get_content_type() == "text/html":
            html_body += content
        elif part.get_content_type() == "text/plain":
            text_body += content

    return text_body, html_body, tuple(attachments), truncated


def _is_attachment(part: Message) -> bool:
    """Diz se uma parte MIME e um anexo.

    Duas pistas: o `Content-Disposition: attachment` explicito, ou a presenca
    de um nome de arquivo. A segunda pega os casos de `inline` com nome, que
    sao anexos para efeitos praticos.
    """
    disposition = str(part.get("Content-Disposition", "")).lower()

    return "attachment" in disposition or bool(part.get_filename())


def _build_attachment(part: Message) -> EmailAttachment | None:
    """Extrai um anexo, respeitando o limite de tamanho."""
    try:
        payload = part.get_payload(decode=True)
    except Exception:  # noqa: BLE001 - codificacao quebrada nao e erro fatal
        return None

    if not payload or len(payload) > MAX_ATTACHMENT_BYTES:
        return None

    return EmailAttachment(
        filename=_decoded_header(part.get_filename()) or "unnamed",
        declared_content_type=part.get_content_type(),
        size=len(payload),
        payload=payload,
    )


def _decoded_text(part: Message) -> str:
    """Decodifica uma parte textual para string.

    `errors="replace"` porque a codificacao declarada pode estar errada ou
    mentindo - e perder o corpo inteiro por causa de um byte invalido seria
    pior que exibi-lo com um caractere trocado.
    """
    try:
        payload = part.get_payload(decode=True)
    except Exception:  # noqa: BLE001
        return ""

    if not payload:
        return ""

    charset = part.get_content_charset() or "utf-8"

    try:
        return payload.decode(charset, errors="replace")
    except LookupError:
        # Charset declarado nao existe. Acontece com mensagens forjadas.
        return payload.decode("utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Links do corpo HTML
# ---------------------------------------------------------------------------


class _LinkExtractor(HTMLParser):
    """Coleta os links de um corpo HTML, com o texto exibido de cada um.

    Usa o parser da biblioteca padrao. Nada e renderizado, nenhum script e
    executado e nenhum recurso externo e buscado - o HTML e tratado como
    texto estruturado, nunca como pagina.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return

        href = dict(attrs).get("href")

        if href:
            self._href = href
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._href is not None:
            self.links.append((self._href, "".join(self._text).strip()))
            self._href = None
            self._text = []


def _extract_links(html: str) -> tuple[EmailLink, ...]:
    """Extrai os links do HTML e marca os que exibem um destino diferente.

    Esta e a tecnica classica de phishing: o texto do link mostra o endereco
    do banco e o `href` aponta para outro lugar. Ver so o texto, ou so a URL,
    nao revela a discrepancia - e preciso comparar os dois.
    """
    extractor = _LinkExtractor()

    try:
        extractor.feed(html)
        extractor.close()
    except Exception:  # noqa: BLE001 - HTML malformado nao e erro fatal
        pass

    return tuple(
        EmailLink(
            url=href,
            display_text=text,
            misleading=is_misleading_link(href, text),
        )
        for href, text in extractor.links[:MAX_URLS]
    )


def _collect_urls(
    text_body: str,
    html_body: str,
    links: tuple[EmailLink, ...],
) -> tuple[str, ...]:
    """Reune todas as URLs da mensagem, sem repeticao.

    Vem de tres lugares: os `href` dos links, o corpo em texto puro, e URLs
    escritas no HTML fora de um link.
    """
    found = [link.url for link in links]
    found.extend(URL_IN_TEXT_PATTERN.findall(text_body))
    found.extend(URL_IN_TEXT_PATTERN.findall(html_body))

    return tuple(dict.fromkeys(found))[:MAX_URLS]
