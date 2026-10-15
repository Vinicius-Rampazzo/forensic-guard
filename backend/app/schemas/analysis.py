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

    disclaimer: str = Field(
        default=(
            "ForensicGuard performs static triage based on indicators and "
            "heuristics. It does not provide a definitive malware or phishing "
            "verdict."
        ),
        description="Always present, and always the same text.",
    )
