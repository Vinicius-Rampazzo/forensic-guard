"""Testes das heuristicas de URL."""

from app.analyzers.url_analyzer import (
    extract_host,
    find_ip_address_urls,
    find_punycode_urls,
    has_ip_address_host,
    has_punycode_domain,
)


class TestHostExtraction:
    """Leitura do host a partir de uma URL nao confiavel."""

    def test_extracts_a_simple_host(self) -> None:
        assert extract_host("https://example.com/path?q=1") == "example.com"

    def test_ignores_port_and_credentials(self) -> None:
        assert extract_host("http://user:pass@example.com:8080/x") == "example.com"

    def test_lowercases_the_host(self) -> None:
        """Dominios nao distinguem maiusculas - a comparacao precisa normalizar."""
        assert extract_host("https://EXAMPLE.COM/") == "example.com"

    def test_returns_none_for_a_string_without_host(self) -> None:
        assert extract_host("not a url at all") is None

    def test_returns_none_instead_of_raising_for_a_malformed_url(self) -> None:
        """URLs vindas de binarios costumam estar truncadas ou corrompidas.

        Uma delas nao pode derrubar a analise inteira.
        """
        assert extract_host("http://[invalido") is None


class TestIpAddressHost:
    """URLs que apontam para endereco IP em vez de dominio."""

    def test_detects_an_ipv4_host(self) -> None:
        assert has_ip_address_host("http://203.0.113.45/payload.bin")

    def test_detects_an_ipv6_host(self) -> None:
        assert has_ip_address_host("http://[2001:db8::1]/x")

    def test_a_domain_is_not_an_ip(self) -> None:
        assert not has_ip_address_host("https://example.com/203.0.113.45")

    def test_a_domain_that_looks_numeric_is_not_an_ip(self) -> None:
        """`1.2.3.4.example.com` tem numeros, mas e um dominio."""
        assert not has_ip_address_host("https://1.2.3.4.example.com/")

    def test_filters_a_list_of_urls(self) -> None:
        urls = [
            "https://example.com/a",
            "http://203.0.113.45/b",
            "https://docs.python.org/3/",
        ]

        assert find_ip_address_urls(urls) == ["http://203.0.113.45/b"]


class TestPunycodeDomain:
    """Dominios codificados em punycode."""

    def test_detects_a_punycode_domain(self) -> None:
        assert has_punycode_domain("https://xn--80ak6aa92e.com/login")

    def test_detects_punycode_in_a_subdomain(self) -> None:
        assert has_punycode_domain("https://xn--pple-43d.example.com/")

    def test_an_ordinary_domain_is_not_punycode(self) -> None:
        assert not has_punycode_domain("https://example.com/")

    def test_the_check_is_per_label_not_substring(self) -> None:
        """`meu-xn--site.com` contem os caracteres, mas nao e punycode.

        A verificacao olha cada rotulo do dominio separadamente. Um "contem a
        string" simples marcaria este caso como suspeito sem motivo.
        """
        assert not has_punycode_domain("https://meu-xn--site.com/")

    def test_filters_a_list_of_urls(self) -> None:
        urls = ["https://example.com/", "https://xn--80ak6aa92e.com/"]

        assert find_punycode_urls(urls) == ["https://xn--80ak6aa92e.com/"]
