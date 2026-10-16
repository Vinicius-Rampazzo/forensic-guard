"""Testes do calculo do Risk Score.

O risk_engine so soma e classifica, entao os testes nao precisam de arquivo
nenhum: bastam indicadores construidos a mao. Essa facilidade de testar e
consequencia direta de ele nao saber nada sobre forense.
"""

import pytest

from app.constants.risk_rules import (
    EXECUTABLE_DISGUISED,
    EXTENSION_MISMATCH,
    MAXIMUM_RISK_SCORE,
    RISK_RULES,
    RISK_THRESHOLDS,
    SUSPICIOUS_COMMAND,
    UNEXPECTED_ENTROPY,
    URL_WITH_IP_HOST,
    RiskLevel,
    RiskRule,
    Severity,
)
from app.services.indicator_engine import Indicator
from app.services.risk_engine import assess, calculate_score, classify


def indicator(rule: RiskRule) -> Indicator:
    """Monta um indicador sem evidencia, para testar apenas a aritmetica."""
    return Indicator(rule=rule, evidence={})


class TestScoreCalculation:
    """Soma dos pesos."""

    def test_no_indicators_scores_zero(self) -> None:
        assert calculate_score([]) == 0

    def test_single_indicator_scores_its_own_weight(self) -> None:
        assert calculate_score([indicator(EXTENSION_MISMATCH)]) == 35

    def test_indicators_are_summed(self) -> None:
        score = calculate_score([indicator(EXTENSION_MISMATCH), indicator(SUSPICIOUS_COMMAND)])

        assert score == 55

    def test_score_is_capped_at_the_maximum(self) -> None:
        """A escala e de 0 a 100 e precisa continuar legivel.

        Sem o teto, muitos indicadores produziriam 140 - numero sem
        significado numa escala centesimal.
        """
        many = [indicator(rule) for rule in RISK_RULES] * 5

        assert calculate_score(many) == MAXIMUM_RISK_SCORE

    def test_informational_indicators_do_not_add_points(self) -> None:
        """Aviso de listagem parcial e honestidade, nao acusacao.

        Um arquivo grande nao e mais perigoso por ser grande.
        """
        from app.constants.risk_rules import STRINGS_LISTING_TRUNCATED

        assert calculate_score([indicator(STRINGS_LISTING_TRUNCATED)]) == 0


class TestClassification:
    """Conversao do score numerico em faixa."""

    @pytest.mark.parametrize(
        ("score", "expected"),
        [
            (0, RiskLevel.LOW),
            (20, RiskLevel.LOW),
            (21, RiskLevel.MEDIUM),
            (50, RiskLevel.MEDIUM),
            (51, RiskLevel.HIGH),
            (75, RiskLevel.HIGH),
            (76, RiskLevel.CRITICAL),
            (100, RiskLevel.CRITICAL),
        ],
    )
    def test_each_boundary_falls_in_the_right_band(
        self, score: int, expected: RiskLevel
    ) -> None:
        """Testa exatamente as bordas de cada faixa.

        Erro de limite - usar `<` onde cabia `<=` - e dos defeitos mais comuns
        e mais silenciosos que existem. Testar 20 e 21, 50 e 51, 75 e 76 pega
        o problema; testar so valores do meio nao pegaria.
        """
        assert classify(score) is expected


class TestAssessment:
    """Avaliacao completa."""

    def test_clean_evidence_scores_zero_and_low(self) -> None:
        result = assess([])

        assert result.score == 0
        assert result.level is RiskLevel.LOW
        assert result.indicators == ()

    def test_disguised_executable_reaches_critical(self) -> None:
        """O caso documentado na especificacao.

        Um executavel disfarcado dispara as duas regras: mismatch de extensao
        (35) e executavel disfarcado (50), totalizando 85 - CRITICAL.
        """
        result = assess([indicator(EXTENSION_MISMATCH), indicator(EXECUTABLE_DISGUISED)])

        assert result.score == 85
        assert result.level is RiskLevel.CRITICAL

    def test_indicators_are_preserved_in_order(self) -> None:
        """Sem a lista de indicadores, o numero seria indefensavel."""
        given = [indicator(UNEXPECTED_ENTROPY), indicator(URL_WITH_IP_HOST)]

        result = assess(given)

        assert [item.rule.id for item in result.indicators] == [
            "file.unexpected_entropy",
            "url.ip_address_host",
        ]


class TestRuleTableIntegrity:
    """Invariantes da tabela de regras - protegem contra erro de digitacao."""

    def test_rule_identifiers_are_unique(self) -> None:
        """Id repetido faria dois indicadores diferentes se confundirem."""
        identifiers = [rule.id for rule in RISK_RULES]

        assert len(identifiers) == len(set(identifiers))

    def test_identifiers_follow_the_area_dot_name_convention(self) -> None:
        """O id vai para o JSON e pode ser usado em automacao.

        Formato estavel e previsivel importa mais do que parece: quem escreve
        um script em cima da API depende dele.
        """
        for rule in RISK_RULES:
            assert "." in rule.id, rule.id
            assert rule.id == rule.id.lower(), rule.id

    def test_scores_are_not_negative(self) -> None:
        """Nenhuma regra pode reduzir o risco de outra."""
        for rule in RISK_RULES:
            assert rule.score >= 0, rule.id

    def test_no_single_rule_exceeds_the_maximum(self) -> None:
        for rule in RISK_RULES:
            assert rule.score <= MAXIMUM_RISK_SCORE, rule.id

    def test_every_rule_explains_itself(self) -> None:
        """Regra sem texto produz indicador que ninguem consegue interpretar."""
        for rule in RISK_RULES:
            assert rule.title.strip(), rule.id
            assert len(rule.description.strip()) > 40, rule.id

    def test_only_informational_rules_score_zero(self) -> None:
        """Peso zero e reservado a avisos, nao a regras mal preenchidas."""
        for rule in RISK_RULES:
            if rule.score == 0:
                assert rule.severity is Severity.INFO, rule.id

    def test_thresholds_are_in_ascending_order(self) -> None:
        """A classificacao percorre os limites em ordem e para no primeiro."""
        bounds = [bound for bound, _ in RISK_THRESHOLDS]

        assert bounds == sorted(bounds)

    def test_the_last_threshold_is_the_maximum_score(self) -> None:
        """Garante que todo score possivel cai em alguma faixa."""
        assert RISK_THRESHOLDS[-1][0] == MAXIMUM_RISK_SCORE
