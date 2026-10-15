"""Contrato da resposta de analise.

Estes modelos sao a fronteira publica do backend: definem exatamente o JSON que
sai da API, alimentam a documentacao automatica em /docs e serao espelhados em
TypeScript quando o frontend for construido.

Mudar um campo aqui e mudar o contrato. Acrescentar campo e compativel;
renomear ou remover quebra quem consome.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.constants.risk_rules import RiskLevel, Severity
from app.constants.signatures import FileCategory
from app.services.evidence_detector import EvidenceType, MismatchKind


class HashesSchema(BaseModel):
    """Impressoes digitais da evidencia.

    MD5 e SHA-1 estao criptograficamente quebrados, mas continuam aqui porque
    bases publicas de indicadores os utilizam. Servem para procurar, nunca
    para confiar.
    """

    md5: str
    sha1: str
    sha256: str = Field(description="Primary identifier shown to the user")
    sha512: str


class ArtifactsSchema(BaseModel):
    """Padroes de interesse forense encontrados nas strings.

    Categorias sem nenhuma ocorrencia sao omitidas - o relatorio nao fica
    cheio de listas vazias.
    """

    urls: list[str] = []
    ipv4: list[str] = []
    ipv6: list[str] = []
    emails: list[str] = []
    windows_paths: list[str] = []
    suspicious_keywords: list[str] = Field(
        default=[],
        description=(
            "Living-off-the-land binaries and execution techniques. Their "
            "presence is not proof of malice: legitimate installers use the "
            "same tools."
        ),
    )


class StringsSchema(BaseModel):
    """Resultado da extracao de strings legiveis.

    A lista completa pode ter milhares de entradas, entao a resposta traz uma
    amostra e informa o total. Os artefatos, que sao o que tem valor forense,
    vem sempre completos.
    """

    total: int = Field(description="How many distinct strings were extracted")
    returned: int = Field(description="How many are included in the sample below")
    truncated: bool = Field(
        description=(
            "True when a safety limit cut the analysis short. The report is "
            "partial and must not be read as a full examination."
        )
    )
    sample: list[str]
    artifacts: ArtifactsSchema


class DetectionSchema(BaseModel):
    """O que a evidencia diz ser, confrontado com o que ela e."""

    evidence_type: EvidenceType = Field(
        description="Which specialised analyser this evidence belongs to"
    )
    declared_extension: str = Field(description="Extension taken from the uploaded filename")
    detected_name: str | None = Field(description="Human readable format name, if recognised")
    detected_mime: str | None = None
    detected_category: FileCategory | None = None
    confirmed_bytes: int = Field(
        description=(
            "How many bytes support the conclusion. Two bytes is weak "
            "evidence, eight is strong."
        )
    )
    ambiguous_with: list[str] = Field(
        default=[],
        description="Other formats whose signature also matched these bytes",
    )
    puremagic_mime: str | None = Field(
        default=None, description="Second opinion from an independent library"
    )
    second_opinion_agrees: bool | None = Field(
        default=None, description="Null when either method had no opinion"
    )
    mismatch: MismatchKind
    notes: list[str] = []


class FileSchema(BaseModel):
    """Caracteristicas gerais do arquivo, independentes do formato."""

    size: int = Field(description="Size in bytes")
    entropy: float = Field(
        ge=0.0,
        le=8.0,
        description=(
            "Shannon entropy in bits per byte. Above 7.5 usually means "
            "compressed or encrypted content - which is common in legitimate "
            "files and is never, on its own, evidence of anything."
        ),
    )
    hashes: HashesSchema


class GpsSchema(BaseModel):
    """Coordenadas em graus decimais, prontas para um mapa."""

    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)


class ImageSchema(BaseModel):
    """Metadados especificos de imagem.

    Presente apenas quando a evidencia foi identificada como imagem. Campos
    vazios sao a norma, nao a excecao: redes sociais removem o EXIF ao
    publicar, entao a maioria das fotos que circulam chega sem metadado algum.
    Ausencia de EXIF nunca e suspeita.
    """

    width: int | None = None
    height: int | None = None
    megapixels: float | None = None
    image_format: str | None = Field(default=None, description="JPEG, PNG, WEBP, ...")
    color_mode: str | None = Field(default=None, description="RGB, RGBA, L, CMYK, ...")

    device_make: str | None = Field(default=None, description="Camera or phone manufacturer")
    device_model: str | None = None
    software: str | None = Field(
        default=None,
        description=(
            "Program that wrote or edited the image. Its presence is not a "
            "finding: most professional photos are edited."
        ),
    )
    created_at: str | None = Field(default=None, description="Timestamp as recorded in EXIF")

    gps: GpsSchema | None = Field(
        default=None,
        description="Where the photo was taken. A privacy matter, not a security one.",
    )

    exif: dict[str, str] = Field(
        default={}, description="Every readable EXIF tag, as text"
    )

    error: str | None = Field(
        default=None,
        description="Why the image could not be read, when it could not be",
    )


class AuthenticationSchema(BaseModel):
    """Veredito de SPF, DKIM e DMARC, lido dos cabecalhos.

    Campos nulos significam que o resultado nao foi informado - o que e
    diferente de ter falhado. Um `.eml` exportado antes da entrega nao passou
    por nenhum servidor verificador.
    """

    spf: str | None = None
    dkim: str | None = None
    dmarc: str | None = None
    raw: str | None = Field(
        default=None, description="The Authentication-Results header as received"
    )


class EmailLinkSchema(BaseModel):
    """Um link do corpo HTML, com o texto que o destinatario enxerga."""

    url: str = Field(description="Where the link actually points")
    display_text: str = Field(description="What the reader sees")
    misleading: bool = Field(
        description="True when the displayed address differs from the destination"
    )


class AttachmentSchema(BaseModel):
    """Um anexo da mensagem, com a sua propria analise completa.

    O campo `analysis` e recursivo: o anexo passa exatamente pelo mesmo
    pipeline do arquivo principal - hashes, entropia, tipo real, mismatch e
    Risk Score proprio. Um PDF anexo que na verdade e um executavel aparece
    aqui com a sua propria nota.

    Fica nulo quando o limite de profundidade impediu a analise.
    """

    filename: str
    declared_content_type: str = Field(
        description="Content type claimed by the message, which may be wrong"
    )
    size: int
    analysis: AnalysisResponse | None = None


class EmailSchema(BaseModel):
    """Metadados e conteudo da mensagem.

    Presente apenas quando a evidencia foi identificada como e-mail.

    Lembrete que vale para quase tudo aqui: **cabecalhos sao escritos por quem
    envia.** `From`, `Subject` e `Date` nao sao verificados por nada. Os
    campos que carregam peso probatorio sao `received_chain` e
    `authentication`, acrescentados pelos servidores pelos quais a mensagem
    passou.
    """

    headers: dict[str, str] = Field(
        default={}, description="Main headers, already MIME-decoded"
    )

    from_address: str | None = None
    from_domain: str | None = None
    reply_to: str | None = None
    reply_to_domain: str | None = None
    return_path: str | None = None
    return_path_domain: str | None = None

    reply_to_mismatch: bool = False
    return_path_mismatch: bool = False

    received_chain: list[str] = Field(
        default=[],
        description="Servers the message passed through, newest first",
    )
    authentication: AuthenticationSchema = AuthenticationSchema()

    has_text_body: bool = False
    has_html_body: bool = False
    urls: list[str] = []
    links: list[EmailLinkSchema] = []

    attachments: list[AttachmentSchema] = []
    attachments_truncated: bool = Field(
        default=False,
        description="True when a safety limit stopped the attachment extraction",
    )

    error: str | None = None


class IndicatorSchema(BaseModel):
    """Uma observacao que mereceu atencao, com o que a justificou.

    O campo `evidence` e o que separa este relatorio de um numero inventado:
    ele traz os dados concretos que dispararam a regra, para que quem le possa
    conferir a conclusao - e discordar dela.
    """

    id: str = Field(description="Stable rule identifier, safe to use in automation")
    title: str
    description: str
    severity: Severity
    score: int = Field(description="How many points this indicator adds to the total")
    evidence: dict[str, Any] = Field(description="The concrete data that triggered the rule")


class RiskSchema(BaseModel):
    """Pontuacao heuristica da evidencia.

    O score e uma soma de observacoes estaticas, limitada a 100. Ele responde
    "isto merece atencao?" - nunca "isto e malware".
    """

    score: int = Field(ge=0, le=100)
    level: RiskLevel
    indicators: list[IndicatorSchema] = Field(
        description="Every indicator that contributed to the score, in order"
    )


class AnalysisResponse(BaseModel):
    """Resposta completa de POST /analyze."""

    filename: str = Field(description="Original filename as sent by the client")
    file: FileSchema
    detection: DetectionSchema
    strings: StringsSchema
    risk: RiskSchema

    image: ImageSchema | None = Field(
        default=None,
        description="Present only when the evidence was identified as an image",
    )
    email: EmailSchema | None = Field(
        default=None,
        description="Present only when the evidence was identified as an email",
    )

    disclaimer: str = Field(
        default=(
            "ForensicGuard performs static triage based on indicators and "
            "heuristics. It does not provide a definitive malware or phishing "
            "verdict."
        ),
        description="Always present, and always the same text.",
    )


# AttachmentSchema aponta para AnalysisResponse, que so e definida depois dela -
# uma referencia circular, porque um e-mail contem anexos que sao, eles
# proprios, evidencias completas.
#
# Com `from __future__ import annotations`, as anotacoes ficam como texto ate
# alguem resolve-las. Esta chamada avisa o Pydantic de que agora todos os nomes
# existem e o modelo pode ser finalizado. Sem ela, o primeiro uso falharia com
# "class not fully defined".
AttachmentSchema.model_rebuild()
