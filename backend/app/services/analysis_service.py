"""Orquestracao da analise de uma evidencia.

Papel na arquitetura
--------------------
Este servico e o unico lugar que conhece as duas pontas da analise: os fatos
genericos do arquivo e a identidade dele.

    api/routes/analysis.py          recebe o upload, trata HTTP
            |
            v
    services/analysis_service.py    <- aqui
            |
            +--> services/evidence_detector.py    o que a evidencia E
            |
            +--> analyzers/file_analyzer.py       hashes, entropia, strings

A rota nao chama os analisadores diretamente, e os analisadores nao sabem o
que e uma requisicao HTTP. Cada camada so enxerga a de baixo.

Nas Etapas 6 e 7, quando os analisadores de imagem e de e-mail existirem, e
aqui que eles serao encaixados - olhando o `evidence_type` que o detector ja
reporta hoje.
"""

from __future__ import annotations

from pathlib import Path

from app.analyzers.email_analyzer import (
    MAX_ATTACHMENT_DEPTH,
    EmailAnalysis,
    analyze_email,
)
from app.analyzers.file_analyzer import FileAnalysis, analyze_file
from app.analyzers.image_analyzer import ImageAnalysis, analyze_image
from app.config import get_settings
from app.constants.signatures import FileCategory
from app.schemas.analysis import (
    AnalysisResponse,
    ArtifactsSchema,
    AttachmentSchema,
    AuthenticationSchema,
    DetectionSchema,
    EmailLinkSchema,
    EmailSchema,
    FileSchema,
    GpsSchema,
    HashesSchema,
    ImageSchema,
    IndicatorSchema,
    RiskSchema,
    StringsSchema,
)
from app.services.evidence_detector import (
    EvidenceDetection,
    EvidenceType,
    detect_evidence,
)
from app.services.indicator_engine import collect_indicators
from app.services.risk_engine import RiskAssessment, assess
from app.utils.temporary_files import temporary_evidence

# Quantas strings acompanham a resposta como amostra.
#
# A extracao pode devolver milhares. Mandar todas tornaria cada resposta
# pesada e a interface inutilizavel - ninguem examina 5.000 linhas. Os
# ARTEFATOS, que sao o que tem valor forense, vao sempre completos; a lista
# crua e so contexto, e uma amostra basta.
STRING_SAMPLE_SIZE = 200


def analyze_evidence(
    path: Path,
    original_filename: str,
    depth: int = 0,
) -> AnalysisResponse:
    """Analisa uma evidencia e monta a resposta da API.

    Args:
        path: arquivo temporario em disco, ja gravado.
        original_filename: nome informado no upload. Vem separado do caminho
            porque o arquivo em disco tem nome gerado por UUID - a extensao a
            ser auditada e a do nome original.
        depth: nivel de aninhamento. Zero para a evidencia enviada pelo
            usuario, um para os anexos dela, e assim por diante.

    Returns:
        A resposta completa, pronta para serializacao.
    """
    file_analysis = analyze_file(path)
    detection = detect_evidence(path, original_filename=original_filename)

    # Analisadores especificos rodam DEPOIS do generico e so quando o tipo
    # detectado os justifica.
    image_analysis = None
    if detection.evidence_type is EvidenceType.IMAGE:
        image_analysis = analyze_image(path)

    email_analysis = None
    attachments: list[AttachmentSchema] = []

    if detection.evidence_type is EvidenceType.EMAIL:
        email_analysis = analyze_email(path)
        attachments = _analyze_attachments(email_analysis, depth)

    # Os fatos primeiro, a interpretacao depois. Os analisadores nao sabem o
    # que e risco, e o risk_engine nao sabe o que e entropia.
    indicators = collect_indicators(
        file_analysis,
        detection,
        image_analysis,
        email_analysis,
        _attachment_categories(attachments),
    )
    risk = assess(indicators)

    return AnalysisResponse(
        filename=original_filename,
        file=_build_file_schema(file_analysis),
        detection=_build_detection_schema(detection),
        strings=_build_strings_schema(file_analysis),
        risk=_build_risk_schema(risk),
        image=_build_image_schema(image_analysis),
        email=_build_email_schema(email_analysis, attachments),
    )


def _analyze_attachments(email: EmailAnalysis, depth: int) -> list[AttachmentSchema]:
    """Analisa cada anexo como se fosse uma evidencia independente.

    Recursao controlada
    -------------------
    Cada anexo passa pelo mesmo pipeline do arquivo principal: hashes,
    entropia, tipo real, mismatch e Risk Score proprio. E isso que faz um
    `fatura.pdf` anexo cujos bytes comecam com `MZ` aparecer como CRITICAL
    dentro do relatorio do e-mail.

    O limite de profundidade existe porque um e-mail pode conter um e-mail que
    contem outro e-mail. Sem teto, um atacante monta uma boneca russa de
    mensagens e a analise desce ate esgotar a pilha ou o disco.

    Ao atingir o limite, o anexo continua listado - nome, tipo declarado e
    tamanho - apenas sem analise. Omiti-lo seria esconder que ele existe.
    """
    if email.error is not None:
        return []

    settings = get_settings()
    results: list[AttachmentSchema] = []

    for attachment in email.attachments:
        entry = AttachmentSchema(
            filename=attachment.filename,
            declared_content_type=attachment.declared_content_type,
            size=attachment.size,
        )

        if depth < MAX_ATTACHMENT_DEPTH:
            with temporary_evidence(settings.temp_dir) as nested_path:
                nested_path.write_bytes(attachment.payload)
                entry.analysis = analyze_evidence(
                    nested_path,
                    original_filename=attachment.filename,
                    depth=depth + 1,
                )

        results.append(entry)

    return results


def _attachment_categories(
    attachments: list[AttachmentSchema],
) -> tuple[tuple[str, FileCategory | None], ...]:
    """Reduz os anexos ao que o Indicator Engine precisa saber deles.

    Ele so precisa do nome e da familia detectada - nao do relatorio inteiro.
    Passar menos informacao do que se tem e uma forma barata de manter os
    modulos independentes.
    """
    return tuple(
        (entry.filename, entry.analysis.detection.detected_category if entry.analysis else None)
        for entry in attachments
    )


def _build_file_schema(analysis: FileAnalysis) -> FileSchema:
    return FileSchema(
        size=analysis.size,
        entropy=analysis.entropy,
        hashes=HashesSchema(**analysis.hashes),
    )


def _build_detection_schema(detection: EvidenceDetection) -> DetectionSchema:
    return DetectionSchema(
        evidence_type=detection.evidence_type,
        declared_extension=detection.declared_extension,
        detected_name=detection.detected_name,
        detected_mime=detection.detected_mime,
        detected_category=detection.detected_category,
        confirmed_bytes=detection.confirmed_bytes,
        ambiguous_with=list(detection.ambiguous_with),
        puremagic_mime=detection.puremagic_mime,
        second_opinion_agrees=detection.second_opinion_agrees,
        mismatch=detection.mismatch,
        notes=list(detection.notes),
    )


def _build_image_schema(analysis: ImageAnalysis | None) -> ImageSchema | None:
    """Converte a analise de imagem para o formato da resposta.

    Devolve None quando a evidencia nao e imagem - e o campo some do JSON, em
    vez de aparecer como um objeto cheio de nulos.
    """
    if analysis is None:
        return None

    gps = None
    if analysis.gps is not None:
        gps = GpsSchema(
            latitude=analysis.gps.latitude,
            longitude=analysis.gps.longitude,
        )

    return ImageSchema(
        width=analysis.width,
        height=analysis.height,
        megapixels=analysis.megapixels,
        image_format=analysis.image_format,
        color_mode=analysis.color_mode,
        device_make=analysis.device_make,
        device_model=analysis.device_model,
        software=analysis.software,
        created_at=analysis.created_at,
        gps=gps,
        exif=analysis.exif,
        error=analysis.error,
    )


def _build_email_schema(
    analysis: EmailAnalysis | None,
    attachments: list[AttachmentSchema],
) -> EmailSchema | None:
    """Converte a analise de e-mail para o formato da resposta."""
    if analysis is None:
        return None

    return EmailSchema(
        headers=analysis.headers,
        from_address=analysis.from_address,
        from_domain=analysis.from_domain,
        reply_to=analysis.reply_to,
        reply_to_domain=analysis.reply_to_domain,
        return_path=analysis.return_path,
        return_path_domain=analysis.return_path_domain,
        reply_to_mismatch=analysis.reply_to_mismatch,
        return_path_mismatch=analysis.return_path_mismatch,
        received_chain=list(analysis.received_chain),
        authentication=AuthenticationSchema(
            spf=analysis.authentication.spf,
            dkim=analysis.authentication.dkim,
            dmarc=analysis.authentication.dmarc,
            raw=analysis.authentication.raw,
        ),
        has_text_body=analysis.has_text_body,
        has_html_body=analysis.has_html_body,
        urls=list(analysis.urls),
        links=[
            EmailLinkSchema(
                url=link.url,
                display_text=link.display_text,
                misleading=link.misleading,
            )
            for link in analysis.links
        ],
        attachments=attachments,
        attachments_truncated=analysis.attachments_truncated,
        error=analysis.error,
    )


def _build_risk_schema(assessment: RiskAssessment) -> RiskSchema:
    """Achata cada indicador para o formato da resposta.

    No dominio, um indicador e "uma regra que disparou mais a evidencia". Na
    API ele vira um objeto plano, porque quem consome nao precisa saber que a
    regra e uma entidade separada - so precisa do id, do texto e do porque.
    """
    return RiskSchema(
        score=assessment.score,
        level=assessment.level,
        indicators=[
            IndicatorSchema(
                id=indicator.rule.id,
                title=indicator.rule.title,
                description=indicator.rule.description,
                severity=indicator.rule.severity,
                score=indicator.rule.score,
                evidence=indicator.evidence,
            )
            for indicator in assessment.indicators
        ],
    )


def _build_strings_schema(analysis: FileAnalysis) -> StringsSchema:
    strings = analysis.strings
    sample = strings.strings[:STRING_SAMPLE_SIZE]

    return StringsSchema(
        total=len(strings.strings),
        returned=len(sample),
        # Verdadeiro tanto quando um limite de seguranca cortou a extracao
        # quanto quando a amostra nao cobre todas as strings encontradas. Nos
        # dois casos o relatorio e parcial, e quem le precisa saber disso.
        truncated=strings.truncated or len(sample) < len(strings.strings),
        sample=sample,
        artifacts=ArtifactsSchema(**strings.artifacts),
    )
