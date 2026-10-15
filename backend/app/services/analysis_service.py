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

from app.analyzers.file_analyzer import FileAnalysis, analyze_file
from app.schemas.analysis import (
    AnalysisResponse,
    ArtifactsSchema,
    DetectionSchema,
    FileSchema,
    HashesSchema,
    IndicatorSchema,
    RiskSchema,
    StringsSchema,
)
from app.services.evidence_detector import EvidenceDetection, detect_evidence
from app.services.indicator_engine import collect_indicators
from app.services.risk_engine import RiskAssessment, assess

# Quantas strings acompanham a resposta como amostra.
#
# A extracao pode devolver milhares. Mandar todas tornaria cada resposta
# pesada e a interface inutilizavel - ninguem examina 5.000 linhas. Os
# ARTEFATOS, que sao o que tem valor forense, vao sempre completos; a lista
# crua e so contexto, e uma amostra basta.
STRING_SAMPLE_SIZE = 200


def analyze_evidence(path: Path, original_filename: str) -> AnalysisResponse:
    """Analisa uma evidencia e monta a resposta da API.

    Args:
        path: arquivo temporario em disco, ja gravado.
        original_filename: nome informado no upload. Vem separado do caminho
            porque o arquivo em disco tem nome gerado por UUID - a extensao a
            ser auditada e a do nome original.

    Returns:
        A resposta completa, pronta para serializacao.
    """
    file_analysis = analyze_file(path)
    detection = detect_evidence(path, original_filename=original_filename)

    # Os fatos primeiro, a interpretacao depois. Os analisadores nao sabem o
    # que e risco, e o risk_engine nao sabe o que e entropia.
    indicators = collect_indicators(file_analysis, detection)
    risk = assess(indicators)

    return AnalysisResponse(
        filename=original_filename,
        file=_build_file_schema(file_analysis),
        detection=_build_detection_schema(detection),
        strings=_build_strings_schema(file_analysis),
        risk=_build_risk_schema(risk),
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
