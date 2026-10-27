"""Testes da resolucao de redirecionamentos.

O que mais importa aqui nao e "seguiu a cadeia certa". E **nao deixou o
servidor ser usado como procurador**. Esta e a unica parte do sistema que faz
requisicao de rede, e quem escolhe o endereco e a pessoa sob investigacao.

Nenhum teste acessa a internet. A rede e substituida por um transporte falso
do httpx, e a resolucao de nomes por uma funcao controlada - teste que depende
de rede falha por motivo errado e esconde regressao de verdade.
"""

from __future__ import annotations

import socket

import httpx2 as httpx
import pytest

from app.analyzers import redirect_resolver
from app.analyzers.redirect_resolver import resolve_redirects
from app.constants.network_policy import MAX_REDIRECT_HOPS

# A implementacao verdadeira, guardada antes de a fixture global substitui-la.
# Os testes de bloqueio precisam dela, e nao do substituto que libera tudo.
resolves_to_blocked = redirect_resolver._resolves_to_blocked_address


@pytest.fixture(autouse=True)
def allow_all_hosts(monkeypatch: pytest.MonkeyPatch) -> None:
    """Por padrao, trata todo nome como publico.

    Os testes que verificam o bloqueio sobrescrevem isto. Sem a fixture, cada
    teste tentaria resolver nomes de verdade no DNS.
    """
    monkeypatch.setattr(
        redirect_resolver, "_resolves_to_blocked_address", lambda host: False
    )


def fake_network(
    monkeypatch: pytest.MonkeyPatch, responses: dict[str, httpx.Response]
) -> None:
    """Substitui a rede por um mapa de URL para resposta."""

    def handler(request: httpx.Request) -> httpx.Response:
        response = responses.get(str(request.url))

        if response is None:
            raise httpx.ConnectError("no route in test", request=request)

        return httpx.Response(
            status_code=response.status_code,
            headers=response.headers,
            request=request,
        )

    transport = httpx.MockTransport(handler)
    original = httpx.Client

    def client(**kwargs: object) -> httpx.Client:
        kwargs["transport"] = transport
        return original(**kwargs)

    monkeypatch.setattr(httpx, "Client", client)


def redirect(to: str, status: int = 302) -> httpx.Response:
    return httpx.Response(status_code=status, headers={"location": to})


def ok() -> httpx.Response:
    return httpx.Response(status_code=200)


class TestChainFollowing:
    """O caminho feliz: seguir ate o destino e relatar os saltos."""

    def test_follows_a_single_redirect(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fake_network(
            monkeypatch,
            {
                "https://encurtador.test/abc": redirect("https://destino.test/pagina"),
                "https://destino.test/pagina": ok(),
            },
        )

        chain = resolve_redirects("https://encurtador.test/abc")

        assert chain.completed is True
        assert chain.final_url == "https://destino.test/pagina"
        assert chain.hop_count == 2

    def test_follows_a_chain_of_several_hops(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake_network(
            monkeypatch,
            {
                "https://a.test/1": redirect("https://b.test/2"),
                "https://b.test/2": redirect("https://c.test/3"),
                "https://c.test/3": ok(),
            },
        )

        chain = resolve_redirects("https://a.test/1")

        assert [hop.host for hop in chain.hops] == ["a.test", "b.test", "c.test"]
        assert chain.final_url == "https://c.test/3"

    def test_resolves_a_relative_location(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`Location` relativo e legal, e o navegador o resolve contra a URL atual."""
        fake_network(
            monkeypatch,
            {
                "https://site.test/velho": redirect("/novo"),
                "https://site.test/novo": ok(),
            },
        )

        chain = resolve_redirects("https://site.test/velho")

        assert chain.final_url == "https://site.test/novo"

    def test_a_url_without_redirect_ends_at_itself(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake_network(monkeypatch, {"https://site.test/": ok()})

        chain = resolve_redirects("https://site.test/")

        assert chain.completed is True
        assert chain.hop_count == 1


class TestServerSideRequestForgery:
    """O grupo que justifica a existencia deste arquivo.

    Seguir redirecionamento de terceiro e deixar outra pessoa escolher o que o
    servidor vai acessar. Cada caso aqui e um ataque real.
    """

    def test_refuses_to_start_at_an_internal_address(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            redirect_resolver, "_resolves_to_blocked_address", lambda host: True
        )

        chain = resolve_redirects("http://10.0.0.5/admin")

        assert chain.completed is False
        assert chain.stopped_reason == "internal_address"
        assert chain.hop_count == 0

    def test_refuses_a_redirect_into_cloud_metadata(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """O ataque classico: inicio publico, destino em 169.254.169.254.

        Esse endereco devolve as credenciais da propria maquina em quase toda
        nuvem. Verificar so o primeiro salto deixaria a porta aberta.
        """
        metadata = "http://169.254.169.254/latest/meta-data/"

        fake_network(
            monkeypatch,
            {"https://inocente.test/x": redirect(metadata), metadata: ok()},
        )
        monkeypatch.setattr(
            redirect_resolver,
            "_resolves_to_blocked_address",
            lambda host: host == "169.254.169.254",
        )

        chain = resolve_redirects("https://inocente.test/x")

        assert chain.stopped_reason == "internal_address"
        assert chain.final_url is None
        # Chegou a registrar o primeiro salto, mas nao conectou no segundo.
        assert [hop.host for hop in chain.hops] == ["inocente.test"]

    def test_refuses_a_redirect_to_a_non_http_scheme(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake_network(
            monkeypatch,
            {"https://inocente.test/x": redirect("file:///etc/passwd")},
        )

        chain = resolve_redirects("https://inocente.test/x")

        assert chain.stopped_reason == "scheme_not_allowed"
        assert chain.final_url is None

    def test_blocked_addresses_cover_more_than_rfc1918(self) -> None:
        """A lista aqui e deliberadamente mais ampla que a do analisador.

        O analisador usa uma lista estreita para relatar sem falso positivo.
        Esta existe para defender, e faixa esquecida vira buraco.
        """
        for address in [
            "127.0.0.1",  # loopback
            "169.254.169.254",  # metadados de nuvem
            "10.1.2.3",  # RFC 1918
            "192.168.0.1",  # RFC 1918
            "172.16.0.1",  # RFC 1918
            "100.64.0.1",  # CGNAT
            "0.0.0.0",  # nao especificado
            "::1",  # loopback IPv6
            "fe80::1",  # link-local IPv6
            "224.0.0.1",  # multicast
        ]:
            assert redirect_resolver._is_blocked_address(address) is True, address

    def test_public_addresses_are_allowed(self) -> None:
        for address in ["8.8.8.8", "45.33.32.156", "2001:4860:4860::8888"]:
            assert redirect_resolver._is_blocked_address(address) is False, address

    def test_a_name_that_does_not_resolve_is_blocked(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Nome inexistente nao leva a lugar nenhum; barrar poupa o tempo da cadeia.

        O resolvedor de nomes e substituido em vez de consultado: teste que
        depende de DNS de verdade falha por motivo errado quando a rede
        oscila, e isso esconde regressao real.
        """

        def falha(*args: object, **kwargs: object) -> None:
            raise socket.gaierror("name does not resolve")

        monkeypatch.setattr(socket, "getaddrinfo", falha)

        assert resolves_to_blocked("qualquer.test") is True

    def test_a_name_resolving_to_mixed_addresses_is_blocked(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Basta UM endereco interno para o ataque funcionar.

        Um nome pode apontar para varios IPs. Verificar so o primeiro deixaria
        passar quem publica um endereco publico na frente e o interno atras.
        """
        monkeypatch.setattr(
            socket,
            "getaddrinfo",
            lambda *a, **k: [
                (None, None, None, None, ("8.8.8.8", 0)),
                (None, None, None, None, ("127.0.0.1", 0)),
            ],
        )

        assert resolves_to_blocked("duas-caras.test") is True


class TestCeilings:
    """Todo laco que cresce com a entrada precisa de teto - regra do projeto."""

    def test_stops_after_too_many_hops(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Cadeia mais longa que o teto, cada salto apontando para o proximo.
        responses = {
            f"https://salto{i}.test/": redirect(f"https://salto{i + 1}.test/")
            for i in range(MAX_REDIRECT_HOPS + 5)
        }
        fake_network(monkeypatch, responses)

        chain = resolve_redirects("https://salto0.test/")

        assert chain.stopped_reason == "too_many_hops"
        assert chain.hop_count == MAX_REDIRECT_HOPS

    def test_detects_a_loop(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fake_network(
            monkeypatch,
            {
                "https://a.test/": redirect("https://b.test/"),
                "https://b.test/": redirect("https://a.test/"),
            },
        )

        chain = resolve_redirects("https://a.test/")

        assert chain.stopped_reason == "loop"
        assert chain.completed is False


class TestFailuresDoNotRaise:
    """Rede e entrada hostil: nada aqui pode derrubar a API."""

    def test_a_connection_error_is_reported_not_raised(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake_network(monkeypatch, {})

        chain = resolve_redirects("https://nao-responde.test/")

        assert chain.completed is False
        assert chain.stopped_reason is not None
        assert chain.stopped_reason.startswith("request_failed")

    def test_garbage_input_does_not_raise(self) -> None:
        for value in ["", "nao e url", "://", "http://", "\x00"]:
            chain = resolve_redirects(value)

            assert chain.completed is False
