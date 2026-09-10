"""Rota de health check.

Um health check responde a uma unica pergunta: "o servico esta de pe?".
Ele nao consulta banco, nao roda analise e nao depende de nada externo -
justamente para que a resposta signifique apenas isso.

Serve ao frontend (mostrar "API online"), a testes de fumaca e, no futuro,
a qualquer ferramenta de monitoramento.
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.schemas.health import HealthResponse

# Um APIRouter agrupa rotas relacionadas. O main.py monta os routers no app.
# Vantagem: cada arquivo de rota vive isolado e o main nao vira um arquivo
# gigante conforme o projeto cresce.
router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(settings: Annotated[Settings, Depends(get_settings)]) -> HealthResponse:
    """Confirma que a API esta respondendo.

    O parametro `settings` usa injecao de dependencia: em vez de a funcao ir
    buscar a configuracao sozinha, o FastAPI a entrega pronta. Isso permite
    que um teste substitua a configuracao sem tocar nesta funcao.
    """
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        version=settings.version,
    )
