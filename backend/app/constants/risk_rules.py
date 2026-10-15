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


# ---------------------------------------------------------------------------
# Regras informativas
# ---------------------------------------------------------------------------

ANALYSIS_TRUNCATED = RiskRule(
    id="analysis.truncated",
    title="Analysis was truncated",
    description=(
        "A safety limit stopped the analysis before the whole file was "
        "examined. The report is partial and absence of findings must not be "
        "read as absence of content."
    ),
    # Pontuacao zero de proposito. O indicador existe para ser honesto sobre o
    # alcance da analise, e nao para pesar contra o arquivo: um arquivo grande
    # nao e mais perigoso por ser grande.
    severity=Severity.INFO,
    score=0,
)


# Todas as regras existentes. Serve a testes de integridade e a quem quiser
# consultar a tabela inteira.
#
# As regras de e-mail (SPF, DKIM, DMARC, Reply-To, Return-Path) e a de anexo
# executavel chegam junto com o analisador de e-mail, na etapa que produzir
# esses dados. Nao adianta definir peso para algo que nada emite.
RISK_RULES: tuple[RiskRule, ...] = (
    EXECUTABLE_DISGUISED,
    EXTENSION_MISMATCH,
    UNEXPECTED_ENTROPY,
    SUSPICIOUS_COMMAND,
    URL_WITH_IP_HOST,
    URL_WITH_PUNYCODE,
    ANALYSIS_TRUNCATED,
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
