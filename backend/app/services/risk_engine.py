"""Calculo do Risk Score a partir dos indicadores encontrados.

Repare no tamanho deste modulo. Ele nao sabe o que e entropia, nao sabe o que
e um executavel e nao sabe ler magic bytes: ele soma numeros e classifica o
resultado. Toda a inteligencia esta no `indicator_engine`, e todos os pesos
estao em `constants/risk_rules.py`.

Essa pequenez e o objetivo, nao um acidente. Quando os pesos forem calibrados
- e eles serao -, nada aqui precisa mudar.

O que o score e, e o que ele nao e
----------------------------------
E uma soma de observacoes estaticas, limitada a 100. Responde "isto merece
atencao de um analista?".

Nao responde "isto e malware". Nenhuma das regras observa comportamento: nada
e executado, nada e aberto, nada e consultado externamente. Um instalador
legitimo pode pontuar alto, e um malware bem feito pode pontuar baixo.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.constants.risk_rules import (
    MAXIMUM_RISK_SCORE,
    RISK_THRESHOLDS,
    RiskLevel,
)
from app.services.indicator_engine import Indicator


@dataclass(frozen=True)
class RiskAssessment:
    """Resultado da avaliacao de risco.

    Attributes:
        score: soma dos pesos, limitada a MAXIMUM_RISK_SCORE.
        level: faixa correspondente ao score.
        indicators: os indicadores que produziram o score, na ordem em que
            foram encontrados. Sem eles o numero seria indefensavel.
    """

    score: int
    level: RiskLevel
    indicators: tuple[Indicator, ...]


def calculate_score(indicators: list[Indicator]) -> int:
    """Soma os pesos dos indicadores, limitando ao maximo.

    O teto existe porque a escala e de 0 a 100 e precisa continuar legivel.
    Sem ele, um arquivo com muitos indicadores produziria 140 - um numero sem
    significado numa escala centesimal.

    O efeito colateral do teto e conhecido e aceito: acima do limite, somar
    mais indicadores nao muda a nota. Para triagem isso nao atrapalha, porque
    a essa altura a conclusao ja e "olhe isto com atencao", e a lista completa
    de indicadores continua visivel no relatorio.
    """
    total = sum(indicator.rule.score for indicator in indicators)
    return min(total, MAXIMUM_RISK_SCORE)


def classify(score: int) -> RiskLevel:
    """Converte o score numerico na faixa correspondente.

    Percorre os limites em ordem crescente e devolve o primeiro que o score
    nao ultrapassa.
    """
    for upper_bound, level in RISK_THRESHOLDS:
        if score <= upper_bound:
            return level

    # Inalcancavel enquanto o ultimo limite for MAXIMUM_RISK_SCORE e o score
    # estiver limitado a ele. Fica como rede de seguranca caso a tabela mude.
    return RiskLevel.CRITICAL


def assess(indicators: list[Indicator]) -> RiskAssessment:
    """Avalia o risco a partir dos indicadores.

    Lista vazia produz score 0 e nivel LOW - o que e uma afirmacao modesta de
    proposito. Significa "a triagem estatica nao encontrou nada que chamasse
    atencao", e nao "este arquivo e seguro".
    """
    score = calculate_score(indicators)

    return RiskAssessment(
        score=score,
        level=classify(score),
        indicators=tuple(indicators),
    )
