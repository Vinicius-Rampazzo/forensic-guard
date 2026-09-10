"""Configuracao compartilhada dos testes.

O conftest.py e um arquivo especial do pytest: tudo que voce define aqui fica
disponivel automaticamente para os testes da pasta, sem precisar importar.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    """Cliente HTTP de teste apontando para uma aplicacao nova.

    O TestClient chama a aplicacao diretamente em memoria - nao sobe servidor,
    nao abre porta, nao depende de rede. Por isso os testes rodam em
    milissegundos e funcionam offline.

    Como usamos a factory create_app(), cada teste recebe uma aplicacao limpa.
    """
    return TestClient(create_app())
