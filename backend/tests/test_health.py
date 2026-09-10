"""Testes da rota de health check.

Sao testes simples de proposito. O valor deles nao esta em cobrir logica
complexa - nao ha logica ali - e sim em provar que a aplicacao monta: config
carregada, router registrado, schema valido. Se algum desses passos quebrar em
uma etapa futura, este teste falha primeiro.
"""

from fastapi.testclient import TestClient


class TestHealthEndpoint:
    """A rota GET /health responde conforme o contrato."""

    def test_responds_with_success(self, client: TestClient) -> None:
        """A rota esta registrada e acessivel."""
        assert client.get("/health").status_code == 200

    def test_payload_matches_the_declared_schema(self, client: TestClient) -> None:
        """O corpo respeita o contrato definido em HealthResponse."""
        payload = client.get("/health").json()

        assert payload["status"] == "ok"
        assert payload["app"] == "ForensicGuard"
        assert "version" in payload


class TestOpenApiDocumentation:
    """A documentacao automatica reflete as rotas existentes."""

    def test_health_route_appears_in_the_schema(self, client: TestClient) -> None:
        """A rota e documentada em /docs e /openapi.json sem esforco manual."""
        schema = client.get("/openapi.json").json()

        assert "/health" in schema["paths"]
