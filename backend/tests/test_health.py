"""Testes da rota de health check.

Sao testes simples de proposito. O valor deles nao esta em cobrir logica
complexa - nao ha logica aqui - e sim em provar que a aplicacao monta:
config carregada, router registrado, schema valido. Se algum desses passos
quebrar em uma etapa futura, este teste falha primeiro.
"""

from fastapi.testclient import TestClient


def test_health_returns_200(client: TestClient) -> None:
    """A rota responde com sucesso."""
    response = client.get("/health")

    assert response.status_code == 200


def test_health_returns_expected_payload(client: TestClient) -> None:
    """O corpo da resposta respeita o contrato definido em HealthResponse."""
    payload = client.get("/health").json()

    assert payload["status"] == "ok"
    assert payload["app"] == "ForensicGuard"
    assert "version" in payload


def test_openapi_schema_documents_health_route(client: TestClient) -> None:
    """A rota aparece na documentacao automatica (/docs e /openapi.json)."""
    schema = client.get("/openapi.json").json()

    assert "/health" in schema["paths"]
