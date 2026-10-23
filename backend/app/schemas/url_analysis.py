"""Contrato da resposta de analise de URL.

Schema proprio, e nao o mesmo da analise de arquivo. Uma URL nao tem tamanho,
nem hashes, nem entropia - devolver esses campos vazios seria sugerir que a
analise falhou neles, quando na verdade eles nao se aplicam.

O que os dois compartilham e a secao `risk`: mesma escala, mesmo formato de
indicador, mesma exigencia de evidencia. E o que faz "70 pontos" significar a
mesma coisa nos dois casos.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.analysis import RiskSchema


class UrlPartsSchema(BaseModel):
    """A URL dissecada.

    Exibir as partes separadas nao e enfeite: a tecnica de phishing mais
    comum depende de o leitor nao perceber onde o dominio de verdade comeca.
    Separar em campos distintos torna isso impossivel de confundir.
    """

    scheme: str
    username: str | None = Field(
        default=None,
        description="Everything before the '@'. The browser ignores it when resolving.",
    )
    has_password: bool = Field(
        default=False,
        description="Whether a password was embedded. The value itself is never returned.",
    )

    host: str
    unicode_host: str | None = Field(
        default=None,
        description=(
            "How the host actually displays when punycode is decoded. Null "
            "when it is already plain ASCII."
        ),
    )
    port: int | None = None

    registrable_domain: str = Field(
        description="The domain that was actually registered — the one that matters."
    )
    subdomains: list[str] = Field(
        default=[], description="Labels before the registrable domain, in order"
    )
    tld: str = ""

    path: str = ""
    query: str = ""
    fragment: str = ""

    is_private_host: bool = Field(
        default=False,
        description=(
            "True for loopback and private network addresses. These are "
            "everyday internal traffic, not the sign of evasion a public IP "
            "would be."
        ),
    )


class UrlAnalysisResponse(BaseModel):
    """Resposta completa de POST /analyze/url."""

    url: str = Field(description="The URL exactly as submitted, trimmed")
    parts: UrlPartsSchema
    risk: RiskSchema

    error: str | None = Field(
        default=None, description="Why the URL could not be parsed, when it could not be"
    )

    analysis_type: str = Field(
        default="url",
        description="Distinguishes this payload from a file analysis response.",
    )

    disclaimer: str = Field(
        default=(
            "ForensicGuard inspects the structure of the address only. No "
            "request is made to it — resolving or visiting a suspicious URL "
            "tells whoever built it that they are being investigated. A "
            "clean result does not mean the destination is safe."
        ),
        description="Always present, and always the same text.",
    )
