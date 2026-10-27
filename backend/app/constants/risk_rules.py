"""Regras de risco: pesos, severidades e faixas de classificacao.

Por que tudo mora aqui
----------------------
Este arquivo e a unica fonte dos numeros do Risk Score. Nenhum peso pode
aparecer solto no meio do codigo.

O motivo nao e organizacao: e auditabilidade. Quem le um relatorio forense tem
direito de saber por que a nota foi aquela, e quem mantem a ferramenta precisa
conseguir ajustar um peso sem cacar numero por dez arquivos. Um `+ 35` escrito
no meio de um `if` e invisivel para as duas pessoas.

Filosofia do score
------------------
O numero e uma HEURISTICA de triagem, nunca um veredito. Ele responde "isto
merece atencao?", e jamais "isto e malware". Toda regra existe para apontar
algo que um analista humano gostaria de olhar - e varias delas disparam em
arquivos perfeitamente legitimos.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Severity(StrEnum):
    """Gravidade de um indicador isolado."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskLevel(StrEnum):
    """Classificacao final da evidencia, derivada da soma dos indicadores."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class RiskRule:
    """Uma regra de triagem.

    Attributes:
        id: identificador estavel, no formato `area.nome`. Entra no JSON e
            pode ser usado por quem automatiza em cima da API - por isso nao
            deve mudar depois de publicado.
        title: titulo curto, exibido no relatorio.
        description: o que a regra observou e o que isso significa. Escrito
            com cuidado para nao soar como acusacao.
        severity: gravidade do indicador isolado.
        score: quantos pontos a regra soma ao total.
    """

    id: str
    title: str
    description: str
    severity: Severity
    score: int


# ---------------------------------------------------------------------------
# Regras de arquivo
# ---------------------------------------------------------------------------

EXECUTABLE_DISGUISED = RiskRule(
    id="file.executable_disguised",
    title="Executable disguised as another file type",
    description=(
        "The file content is an executable program, but its name suggests a "
        "document, image or other harmless type. This is a common malware "
        "delivery technique: the user believes they are opening a file and "
        "instead runs a program."
    ),
    severity=Severity.CRITICAL,
    score=50,
)

EXTENSION_MISMATCH = RiskRule(
    id="file.extension_mismatch",
    title="File extension does not match the detected signature",
    description=(
        "The filename extension does not correspond to the file format "
        "identified from its first bytes. This can be a renamed file, a "
        "wrong extension, or a deliberate attempt to disguise the content."
    ),
    severity=Severity.HIGH,
    score=35,
)

UNEXPECTED_ENTROPY = RiskRule(
    id="file.unexpected_entropy",
    title="Unexpectedly high entropy",
    description=(
        "The byte distribution is close to random, which usually means "
        "compressed, encrypted or packed content. That is normal in archives "
        "and media files, but unexpected in this format."
    ),
    severity=Severity.LOW,
    score=10,
)


# ---------------------------------------------------------------------------
# Regras de conteudo
# ---------------------------------------------------------------------------

SUSPICIOUS_COMMAND = RiskRule(
    id="strings.suspicious_command",
    title="References to command interpreters or execution techniques",
    description=(
        "The file contains references to Windows binaries commonly abused to "
        "run code, or to execution and obfuscation techniques. Legitimate "
        "installers and administration scripts use the same tools, so this "
        "is context, not proof."
    ),
    severity=Severity.MEDIUM,
    score=20,
)


# ---------------------------------------------------------------------------
# Regras de URL
# ---------------------------------------------------------------------------

URL_WITH_IP_HOST = RiskRule(
    id="url.ip_address_host",
    title="URL pointing to a bare IP address",
    description=(
        "A URL uses an IP address instead of a domain name. This avoids "
        "domain registration and reputation checks, and is unusual in "
        "legitimate content aimed at people."
    ),
    severity=Severity.MEDIUM,
    score=15,
)

URL_WITH_PUNYCODE = RiskRule(
    id="url.punycode_domain",
    title="URL with a punycode domain",
    description=(
        "A URL uses a punycode (xn--) domain, which encodes non-ASCII "
        "characters. The mechanism is legitimate and used worldwide, but it "
        "also allows domains that look identical to well-known brands."
    ),
    severity=Severity.MEDIUM,
    score=15,
)

URL_DANGEROUS_SCHEME = RiskRule(
    id="url.dangerous_scheme",
    title="URL uses a code-executing or content-embedding scheme",
    description=(
        "The address does not point to a server — it carries code or an "
        "entire document inside itself. A `data:` link can hold a complete "
        "phishing form with no domain to report and no server to take down."
    ),
    severity=Severity.CRITICAL,
    score=40,
)

URL_MIXED_SCRIPTS = RiskRule(
    id="url.mixed_scripts",
    title="Domain mixes different writing systems",
    description=(
        "The domain combines characters from more than one alphabet — for "
        "example a Cyrillic 'а' inside an otherwise Latin name. The result "
        "is visually identical to the legitimate domain while being a "
        "completely different address."
    ),
    severity=Severity.HIGH,
    score=30,
)

URL_WITH_CREDENTIALS = RiskRule(
    id="url.credentials_in_url",
    title="URL embeds credentials before the host",
    description=(
        "Everything before the `@` is treated as a username by the browser "
        "and ignored when resolving the address. `http://banco.com@evil."
        "example` goes to evil.example while reading as the bank's site."
    ),
    severity=Severity.HIGH,
    score=25,
)

URL_EXECUTABLE_PATH = RiskRule(
    id="url.executable_download",
    title="URL points directly to an executable",
    description=(
        "The path ends in an extension that runs when opened. Software "
        "vendors distribute installers this way, but in a link received by "
        "email it is usually the final delivery step."
    ),
    severity=Severity.HIGH,
    score=30,
)

URL_DOUBLE_EXTENSION = RiskRule(
    id="url.double_extension",
    title="URL path uses a double extension",
    description=(
        "The filename ends in a harmless extension followed by an executable "
        "one, like `invoice.pdf.exe`. Systems that hide the final extension "
        "— the Windows default — display it as `invoice.pdf`."
    ),
    severity=Severity.HIGH,
    score=25,
)

URL_RISKY_TLD = RiskRule(
    id="url.risky_tld",
    title="Domain uses a top-level domain with high abuse rates",
    description=(
        "The TLD is either free to register without verification, or it "
        "collides with a file extension — `.zip` and `.mov` make the text "
        "`report.zip` into a clickable link to someone else's domain."
    ),
    severity=Severity.MEDIUM,
    score=15,
)

URL_REDIRECTOR_SHAPE = RiskRule(
    id="url.redirector_shape",
    title="Address is shaped like a link redirector",
    description=(
        "The domain is short, there is a single path segment that looks "
        "generated rather than written, and there are no parameters. That is "
        "the shape of a redirector, even when the service is not a known one "
        "- and anyone can host their own. As with any redirector, the "
        "destination is hidden until the link is followed."
    ),
    severity=Severity.LOW,
    score=10,
)

URL_SHORTENER = RiskRule(
    id="url.shortener",
    title="URL uses a link shortening service",
    description=(
        "Shorteners are a common and legitimate service. What they do for "
        "this analysis is hide the destination: there is no way to judge "
        "where it leads without visiting it, and visiting is exactly what an "
        "offline triage does not do."
    ),
    severity=Severity.LOW,
    score=10,
)

URL_EXCESSIVE_SUBDOMAINS = RiskRule(
    id="url.excessive_subdomains",
    title="Domain is buried under many subdomains",
    description=(
        "A familiar name sits at the start of the address while the actual "
        "registered domain is at the end — `banco.com.br.seguranca.example."
        "com` belongs to example.com. The eye stops at the beginning."
    ),
    severity=Severity.MEDIUM,
    score=10,
)

URL_INSECURE_SCHEME = RiskRule(
    id="url.insecure_scheme",
    title="URL uses HTTP without encryption",
    description=(
        "Traffic is readable and modifiable in transit. Common on internal "
        "networks, unusual for a public page — and especially so for one "
        "asking for a password."
    ),
    severity=Severity.LOW,
    score=10,
)

URL_NON_STANDARD_PORT = RiskRule(
    id="url.non_standard_port",
    title="URL uses a non-standard port",
    description=(
        "Public-facing services almost always use the default port. A high "
        "or unusual port often indicates improvised infrastructure."
    ),
    severity=Severity.LOW,
    score=10,
)

URL_OBFUSCATED = RiskRule(
    id="url.obfuscated",
    title="URL is obscured by encoding or length",
    description=(
        "Heavy percent-encoding, a numeric host, or an address long enough "
        "to push the real domain out of the visible address bar. Each makes "
        "the destination harder to read at a glance."
    ),
    severity=Severity.MEDIUM,
    score=15,
)


# ---------------------------------------------------------------------------
# Regras de e-mail
#
# Os pesos seguem a especificacao. Note que SPF e DMARC pesam mais que DKIM:
# os dois primeiros verificam se o servidor tinha autorizacao para enviar em
# nome daquele dominio, enquanto o DKIM falha com frequencia por motivos
# inocentes - listas de discussao e encaminhamentos quebram a assinatura ao
# alterar o corpo da mensagem.
# ---------------------------------------------------------------------------

SPF_FAILED = RiskRule(
    id="email.spf_failed",
    title="SPF verification failed",
    description=(
        "The receiving server reported that the sending machine was not "
        "authorised to send mail for the claimed domain. SPF is one of the "
        "few parts of an email that the sender cannot forge."
    ),
    severity=Severity.HIGH,
    score=15,
)

DKIM_FAILED = RiskRule(
    id="email.dkim_failed",
    title="DKIM signature failed",
    description=(
        "The cryptographic signature covering the message did not verify. "
        "This often happens for innocent reasons: mailing lists and "
        "forwarding rewrite the body and break the signature."
    ),
    severity=Severity.MEDIUM,
    score=10,
)

DMARC_FAILED = RiskRule(
    id="email.dmarc_failed",
    title="DMARC policy evaluation failed",
    description=(
        "The domain owner published a policy stating how to treat messages "
        "that fail authentication, and this message failed it. DMARC builds "
        "on SPF and DKIM, so this usually accompanies one of them."
    ),
    severity=Severity.HIGH,
    score=15,
)

REPLY_TO_MISMATCH = RiskRule(
    id="email.reply_to_mismatch",
    title="Reply-To points to a different domain than the sender",
    description=(
        "Answering this message would send the reply somewhere other than "
        "the apparent sender's domain. It is a common way to collect "
        "responses while appearing to be a known organisation — although "
        "newsletters and ticketing systems legitimately do the same."
    ),
    severity=Severity.MEDIUM,
    score=10,
)

RETURN_PATH_MISMATCH = RiskRule(
    id="email.return_path_mismatch",
    title="Return-Path differs from the sender domain",
    description=(
        "Bounces for this message would go to a different domain than the "
        "one it claims to come from. Marketing platforms and mailing lists "
        "do this routinely, so on its own the finding is weak."
    ),
    severity=Severity.LOW,
    score=10,
)

MISLEADING_LINK = RiskRule(
    id="email.misleading_link",
    title="Link text does not match its destination",
    description=(
        "A link displays one address and points to another. Reading the "
        "message, the recipient sees a familiar domain; clicking takes them "
        "somewhere else. This is the defining technique of phishing."
    ),
    severity=Severity.HIGH,
    score=20,
)

EXECUTABLE_ATTACHMENT = RiskRule(
    id="email.executable_attachment",
    title="Message carries an executable attachment",
    description=(
        "One of the attachments is an executable program or a script. "
        "Legitimate correspondence almost never sends one, and most mail "
        "providers block them precisely for this reason."
    ),
    severity=Severity.CRITICAL,
    score=30,
)


# ---------------------------------------------------------------------------
# Regras de imagem
# ---------------------------------------------------------------------------

DECOMPRESSION_BOMB = RiskRule(
    id="image.decompression_bomb",
    title="Image declares an implausible number of pixels",
    description=(
        "The image header declares dimensions far beyond any real camera. "
        "Decoding it would require enormous amounts of memory, which is the "
        "point of a decompression bomb: a small file that exhausts the "
        "resources of whatever opens it. ForensicGuard never decodes the "
        "pixels, so the file was inspected safely."
    ),
    severity=Severity.HIGH,
    score=25,
)


# ---------------------------------------------------------------------------
# Regras informativas
# ---------------------------------------------------------------------------

GPS_COORDINATES = RiskRule(
    id="image.gps_coordinates",
    title="Image contains GPS coordinates",
    description=(
        "The image carries the location where it was taken. This is a "
        "privacy matter, not a security one: people are often unaware that "
        "sharing a photo also shares where they live or work."
    ),
    # Zero ponto. Localizacao embutida nao torna a evidencia perigosa - torna
    # a pessoa que a enviou exposta. O indicador existe para avisar, nunca
    # para acusar.
    severity=Severity.INFO,
    score=0,
)

STRINGS_LISTING_TRUNCATED = RiskRule(
    id="strings.listing_truncated",
    title="String listing is partial",
    description=(
        "A safety limit stopped the string extraction early. Hashes, entropy "
        "and type detection still cover the whole file, and the artifacts "
        "below are complete — only the raw list of readable text is cut "
        "short. A string missing from that list may still be in the file."
    ),
    # Pontuacao zero de proposito. O indicador existe para ser honesto sobre o
    # alcance da analise, e nao para pesar contra o arquivo: um arquivo grande
    # nao e mais perigoso por ser grande.
    severity=Severity.INFO,
    score=0,
)


# Todas as regras existentes. Serve a testes de integridade e a quem quiser
# consultar a tabela inteira.
RISK_RULES: tuple[RiskRule, ...] = (
    EXECUTABLE_DISGUISED,
    EXTENSION_MISMATCH,
    UNEXPECTED_ENTROPY,
    SUSPICIOUS_COMMAND,
    URL_WITH_IP_HOST,
    URL_WITH_PUNYCODE,
    URL_DANGEROUS_SCHEME,
    URL_MIXED_SCRIPTS,
    URL_WITH_CREDENTIALS,
    URL_EXECUTABLE_PATH,
    URL_DOUBLE_EXTENSION,
    URL_RISKY_TLD,
    URL_SHORTENER,
    URL_REDIRECTOR_SHAPE,
    URL_EXCESSIVE_SUBDOMAINS,
    URL_INSECURE_SCHEME,
    URL_NON_STANDARD_PORT,
    URL_OBFUSCATED,
    SPF_FAILED,
    DKIM_FAILED,
    DMARC_FAILED,
    REPLY_TO_MISMATCH,
    RETURN_PATH_MISMATCH,
    MISLEADING_LINK,
    EXECUTABLE_ATTACHMENT,
    DECOMPRESSION_BOMB,
    GPS_COORDINATES,
    STRINGS_LISTING_TRUNCATED,
)


# ---------------------------------------------------------------------------
# Classificacao
# ---------------------------------------------------------------------------

MAXIMUM_RISK_SCORE = 100

# Limite superior de cada faixa, em ordem crescente. O primeiro limite que o
# score nao ultrapassa define a classificacao.
#
#     0 - 20    LOW
#    21 - 50    MEDIUM
#    51 - 75    HIGH
#    76 - 100   CRITICAL
RISK_THRESHOLDS: tuple[tuple[int, RiskLevel], ...] = (
    (20, RiskLevel.LOW),
    (50, RiskLevel.MEDIUM),
    (75, RiskLevel.HIGH),
    (MAXIMUM_RISK_SCORE, RiskLevel.CRITICAL),
)


# ---------------------------------------------------------------------------
# Parametros das regras
# ---------------------------------------------------------------------------

# Acima deste valor a distribuicao de bytes e considerada quase aleatoria.
#
# Texto natural fica perto de 4.5; um executavel comum, perto de 6. Passar de
# 7.2 indica compressao, criptografia ou empacotamento.
HIGH_ENTROPY_THRESHOLD = 7.2

# Formatos em que entropia alta e o comportamento NORMAL, por serem comprimidos
# por natureza. Disparar o indicador neles encheria o relatorio de ruido: toda
# foto e todo arquivo compactado viraria alerta, e o usuario aprenderia a
# ignorar o score.
#
# Identificados por MIME porque varios formatos compartilham o mesmo tipo.
#
# Repare que executaveis NAO estao na lista: entropia alta num programa sugere
# empacotamento (packing), que e justamente o que se quer observar. E formatos
# sem compressao - BMP, TIFF, WAV - tambem ficam de fora, porque neles o valor
# alto e genuinamente estranho.
NATURALLY_COMPRESSED_MIMES = frozenset(
    {
        "application/zip",
        "application/vnd.rar",
        "application/x-7z-compressed",
        "application/gzip",
        "application/x-bzip2",
        "application/x-xz",
        "application/pdf",
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "image/heic",
        "audio/mpeg",
        "video/mp4",
        "video/x-msvideo",
    }
)
