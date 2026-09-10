"""Schema da resposta do health check.

Um schema Pydantic define o CONTRATO da API: quais campos existem e de que
tipo. Ele serve para tres coisas ao mesmo tempo:

1. valida a resposta antes de enviar (se o codigo devolver algo fora do
   formato, o erro aparece aqui e nao no frontend);
2. documenta a rota automaticamente no /docs;
3. da ao frontend um formato estavel para espelhar em TypeScript.

Este e o mesmo padrao que os schemas de analise vao seguir mais adiante.
"""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Resposta de GET /health."""

    status: str
    app: str
    version: str
