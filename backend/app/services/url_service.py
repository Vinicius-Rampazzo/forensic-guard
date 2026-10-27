"""Analise de uma URL enviada diretamente pelo usuario.

Mesma arquitetura da analise de arquivo, mesmo Risk Engine, mesma escala de
0 a 100 - muda apenas a evidencia de entrada.

    analyzers/url_analyzer.py    observa a estrutura da URL
            |
            v
    services/url_service.py      <- aqui: traduz observacoes em indicadores
            |
            v
    services/risk_engine.py      soma os pesos e classifica

Reaproveitar o risk_engine nao e economia de codigo: e o que garante que um
link com 70 pontos signifique a mesma coisa que um arquivo com 70 pontos.
Duas escalas separadas seriam duas ferramentas.
"""

from __future__ import annotations

from app.analyzers.redirect_resolver import resolve_redirects
from app.analyzers.url_analyzer import UrlAnalysis, analyze_url
from app.constants.risk_rules import (
    URL_DANGEROUS_SCHEME,
    URL_DOUBLE_EXTENSION,
    URL_EXCESSIVE_SUBDOMAINS,
    URL_EXECUTABLE_PATH,
    URL_INSECURE_SCHEME,
    URL_MIXED_SCRIPTS,
    URL_NON_STANDARD_PORT,
    URL_OBFUSCATED,
    URL_REDIRECTOR_SHAPE,
    URL_RISKY_TLD,
    URL_SHORTENER,
    URL_WITH_CREDENTIALS,
    URL_WITH_IP_HOST,
    URL_WITH_PUNYCODE,
    RiskRule,
)
from app.schemas.analysis import IndicatorSchema, RiskSchema
from app.schemas.url_analysis import (
    RedirectHopSchema,
    UrlAnalysisResponse,
    UrlPartsSchema,
    UrlResolutionResponse,
)
from app.services.indicator_engine import Indicator
from app.services.risk_engine import assess


def analyze_url_evidence(raw_url: str) -> UrlAnalysisResponse:
    """Analisa uma URL e monta a resposta da API."""
    analysis = analyze_url(raw_url)
    indicators = collect_url_indicators(analysis)
    risk = assess(indicators)

    return UrlAnalysisResponse(
        url=analysis.url,
        parts=_build_parts_schema(analysis),
        risk=RiskSchema(
            score=risk.score,
            level=risk.level,
            indicators=[
                IndicatorSchema(
                    id=indicator.rule.id,
                    title=indicator.rule.title,
                    description=indicator.rule.description,
                    severity=indicator.rule.severity,
                    score=indicator.rule.score,
                    evidence=indicator.evidence,
                )
                for indicator in risk.indicators
            ],
        ),
        error=analysis.error,
    )


def collect_url_indicators(analysis: UrlAnalysis) -> list[Indicator]:
    """Traduz as caracteristicas observadas em indicadores.

    A ordem e estavel, do mais grave ao mais sutil. Resultado que muda de
    ordem sozinho e impossivel de testar.
    """
    if analysis.error is not None:
        return []

    parts = analysis.parts
    indicators: list[Indicator] = []

    def add(rule: RiskRule, **evidence: object) -> None:
        indicators.append(Indicator(rule=rule, evidence=dict(evidence)))

    if analysis.dangerous_scheme:
        add(URL_DANGEROUS_SCHEME, scheme=f"{parts.scheme}:")

    if analysis.mixed_scripts:
        add(
            URL_MIXED_SCRIPTS,
            displayed_as=parts.unicode_host,
            encoded_as=parts.host,
            writing_systems=list(analysis.scripts_found),
        )

    if analysis.executable_path:
        add(URL_EXECUTABLE_PATH, path=parts.path)

    if analysis.has_credentials:
        add(
            URL_WITH_CREDENTIALS,
            # A senha nunca e exibida: ela pode ser real, de alguem que colou
            # a propria URL de acesso por engano.
            username=parts.username,
            password_present=parts.password is not None,
            actual_host=parts.host,
        )

    if analysis.double_extension:
        add(URL_DOUBLE_EXTENSION, path=parts.path)

    if analysis.ip_address_host:
        add(URL_WITH_IP_HOST, host=parts.host)

    if analysis.punycode_domain:
        add(URL_WITH_PUNYCODE, encoded_as=parts.host, displayed_as=parts.unicode_host)

    if analysis.risky_tld:
        add(URL_RISKY_TLD, tld=f".{parts.tld}", domain=parts.registrable_domain)

    if analysis.excessive_subdomains:
        add(
            URL_EXCESSIVE_SUBDOMAINS,
            subdomains=list(parts.subdomains),
            actual_domain=parts.registrable_domain,
        )

    if analysis.url_shortener:
        add(URL_SHORTENER, service=parts.registrable_domain)

    if analysis.redirector_shape:
        add(
            URL_REDIRECTOR_SHAPE,
            host=parts.host,
            identifier=parts.path.lstrip("/"),
        )

    if analysis.non_standard_port:
        add(URL_NON_STANDARD_PORT, port=parts.port, scheme=parts.scheme)

    if analysis.insecure_scheme:
        add(URL_INSECURE_SCHEME, scheme=parts.scheme)

    # Comprimento, codificacao pesada e host numerico sao formas diferentes do
    # mesmo problema - a URL esconder o proprio destino - entao compartilham
    # uma regra e aparecem como um indicador so.
    if analysis.heavy_encoding or analysis.excessive_length or analysis.numeric_host:
        reasons = []
        if analysis.heavy_encoding:
            reasons.append("heavy percent-encoding")
        if analysis.numeric_host:
            reasons.append("numeric host")
        if analysis.excessive_length:
            reasons.append(f"{len(analysis.url)} characters long")

        add(URL_OBFUSCATED, reasons=reasons)

    return indicators


def _build_parts_schema(analysis: UrlAnalysis) -> UrlPartsSchema:
    parts = analysis.parts

    return UrlPartsSchema(
        scheme=parts.scheme,
        username=parts.username,
        has_password=parts.password is not None,
        host=parts.host,
        unicode_host=parts.unicode_host if parts.unicode_host != parts.host else None,
        port=parts.port,
        registrable_domain=parts.registrable_domain,
        subdomains=list(parts.subdomains),
        tld=parts.tld,
        path=parts.path,
        query=parts.query,
        fragment=parts.fragment,
        is_private_host=analysis.private_host,
    )


def resolve_url_destination(raw_url: str) -> UrlResolutionResponse:
    """Segue os redirecionamentos e analisa onde a URL realmente termina.

    Esta e a unica operacao do sistema que toca a rede, e por isso ela vive
    num servico proprio, atras de um endpoint proprio. `analyze_url_evidence`
    continua sendo offline do comeco ao fim.

    O destino final passa pela MESMA analise da URL enviada. Isso importa: um
    encurtador que leva a `paypa1-seguranca.tk/login.exe` precisa produzir os
    mesmos indicadores que apareceriam se aquele endereco tivesse sido colado
    direto. Analisar so o inicio da cadeia seria parar justamente onde a
    informacao comeca.
    """
    chain = resolve_redirects(raw_url.strip())

    hops = [
        RedirectHopSchema(url=hop.url, host=hop.host, status_code=hop.status_code)
        for hop in chain.hops
    ]

    # Sem destino confirmado nao ha o que analisar. Devolver a cadeia parcial
    # ainda e util: ela mostra ate onde foi e por que parou.
    destination = (
        analyze_url_evidence(chain.final_url) if chain.completed and chain.final_url else None
    )

    return UrlResolutionResponse(
        start_url=chain.start_url,
        hops=hops,
        final_url=chain.final_url,
        completed=chain.completed,
        stopped_reason=chain.stopped_reason,
        destination=destination,
    )
