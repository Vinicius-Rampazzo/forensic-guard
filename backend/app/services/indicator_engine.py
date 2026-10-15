"""Extracao de indicadores a partir dos fatos observados.

Papel na arquitetura
--------------------
    analise (hashes, entropia, strings, tipo)
            |
            v
    indicator_engine    <- aqui: traduz FATOS em INDICADORES
            |
            v
    risk_engine         soma os pesos e classifica

A separacao entre os dois ultimos existe porque eles mudam por motivos
diferentes. Os pesos sao calibrados com o tempo; a leitura dos fatos, nao. O
risk_engine nem sabe o que e entropia - ele so soma numeros.

Explicabilidade
---------------
Todo indicador carrega a **evidencia** que o disparou. Essa e a regra que
separa uma ferramenta forense util de um numero inventado: quem le o relatorio
precisa conseguir verificar a conclusao por conta propria, e discordar dela se
for o caso.

    score sem evidencia = opiniao
    score com evidencia = observacao verificavel
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.analyzers.file_analyzer import FileAnalysis
from app.analyzers.url_analyzer import find_ip_address_urls, find_punycode_urls
from app.constants.risk_rules import (
    ANALYSIS_TRUNCATED,
    EXECUTABLE_DISGUISED,
    EXTENSION_MISMATCH,
    HIGH_ENTROPY_THRESHOLD,
    NATURALLY_COMPRESSED_MIMES,
    SUSPICIOUS_COMMAND,
    UNEXPECTED_ENTROPY,
    URL_WITH_IP_HOST,
    URL_WITH_PUNYCODE,
    RiskRule,
)
from app.services.evidence_detector import EvidenceDetection, MismatchKind


@dataclass(frozen=True)
class Indicator:
    """Uma regra que disparou, com a evidencia que a justificou.

    Attributes:
        rule: a regra, com id, titulo, descricao, severidade e peso.
        evidence: os dados concretos que provocaram o disparo. Precisa ser
            serializavel em JSON, porque vai inteiro para a resposta da API.
    """

    rule: RiskRule
    evidence: dict[str, Any]


def collect_indicators(
    analysis: FileAnalysis,
    detection: EvidenceDetection,
) -> list[Indicator]:
    """Reune todos os indicadores aplicaveis a uma evidencia.

    A ordem e estavel: regras de arquivo, depois de conteudo, depois de URL, e
    por fim as informativas. Resultado que muda de ordem sozinho e impossivel
    de testar e desconfortavel de ler.
    """
    return [
        *_mismatch_indicators(detection),
        *_entropy_indicators(analysis, detection),
        *_string_indicators(analysis),
        *_url_indicators(analysis),
        *_truncation_indicators(analysis),
    ]


def _mismatch_indicators(detection: EvidenceDetection) -> list[Indicator]:
    """Indicadores derivados da contradicao entre nome e conteudo.

    Um executavel disfarcado dispara DUAS regras, e isso e proposital: ele e
    um mismatch de extensao (+35) E um executavel disfarcado (+50), somando
    85 - a faixa CRITICAL. Sao duas observacoes distintas sobre o mesmo fato,
    e cada uma aparece no relatorio com sua propria explicacao.
    """
    if detection.mismatch is MismatchKind.NONE:
        return []

    evidence = {
        "declared_extension": detection.declared_extension,
        "detected_type": detection.detected_name,
        "detected_mime": detection.detected_mime,
        "confirmed_bytes": detection.confirmed_bytes,
    }

    indicators = [Indicator(rule=EXTENSION_MISMATCH, evidence=evidence)]

    if detection.mismatch is MismatchKind.EXECUTABLE_DISGUISED:
        indicators.append(Indicator(rule=EXECUTABLE_DISGUISED, evidence=evidence))

    return indicators


def _entropy_indicators(
    analysis: FileAnalysis,
    detection: EvidenceDetection,
) -> list[Indicator]:
    """Indicador de entropia alta, apenas quando ela e inesperada.

    Arquivos compactados e de midia tem entropia alta por construcao. Marcar
    todos eles encheria o relatorio de ruido e ensinaria o usuario a ignorar o
    score - o pior resultado possivel para uma ferramenta de triagem.

    Num `.txt`, num documento ou num formato desconhecido, por outro lado, o
    mesmo valor e genuinamente estranho. Em executaveis tambem: ali sugere
    empacotamento, que e exatamente o que se quer observar.
    """
    if analysis.entropy <= HIGH_ENTROPY_THRESHOLD:
        return []

    if detection.detected_mime in NATURALLY_COMPRESSED_MIMES:
        return []

    return [
        Indicator(
            rule=UNEXPECTED_ENTROPY,
            evidence={
                "entropy": round(analysis.entropy, 4),
                "threshold": HIGH_ENTROPY_THRESHOLD,
                "detected_type": detection.detected_name,
            },
        )
    ]


def _string_indicators(analysis: FileAnalysis) -> list[Indicator]:
    """Indicador de referencias a interpretadores e tecnicas de execucao."""
    keywords = analysis.strings.artifacts.get("suspicious_keywords", [])

    if not keywords:
        return []

    return [Indicator(rule=SUSPICIOUS_COMMAND, evidence={"keywords": keywords})]


def _url_indicators(analysis: FileAnalysis) -> list[Indicator]:
    """Indicadores derivados das URLs encontradas no conteudo."""
    urls = analysis.strings.artifacts.get("urls", [])

    if not urls:
        return []

    indicators = []

    if ip_urls := find_ip_address_urls(urls):
        indicators.append(Indicator(rule=URL_WITH_IP_HOST, evidence={"urls": ip_urls}))

    if punycode_urls := find_punycode_urls(urls):
        indicators.append(Indicator(rule=URL_WITH_PUNYCODE, evidence={"urls": punycode_urls}))

    return indicators


def _truncation_indicators(analysis: FileAnalysis) -> list[Indicator]:
    """Aviso de que a analise nao cobriu o arquivo inteiro.

    Vale zero ponto: um arquivo grande nao e mais perigoso por ser grande. O
    indicador existe para ser honesto sobre o alcance do exame - sem ele, a
    ausencia de achados poderia ser lida como ausencia de conteudo.
    """
    if not analysis.strings.truncated:
        return []

    return [
        Indicator(
            rule=ANALYSIS_TRUNCATED,
            evidence={"strings_extracted": len(analysis.strings.strings)},
        )
    ]
