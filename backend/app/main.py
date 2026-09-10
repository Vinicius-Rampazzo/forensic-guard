"""Ponto de entrada da API do ForensicGuard.

Este arquivo faz apenas tres coisas: cria a aplicacao, liga os middlewares e
registra os routers. Nenhuma regra de negocio mora aqui.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import health
from app.config import get_settings


def create_app() -> FastAPI:
    """Cria e configura a aplicacao FastAPI.

    Esse padrao se chama *application factory*: em vez de criar o objeto solto
    no topo do modulo, criamos dentro de uma funcao. O ganho e para os testes -
    cada teste pode montar uma aplicacao limpa, com a configuracao que quiser,
    sem herdar estado de execucoes anteriores.
    """
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        description=(
            "Open-source forensic triage tool for inspecting files, images and "
            "emails for suspicious indicators, metadata anomalies and potential "
            "security threats."
        ),
    )

    # CORS: o navegador bloqueia, por padrao, uma pagina servida em
    # localhost:3000 que tente chamar 127.0.0.1:8000 - host e porta diferentes
    # significam "origem" diferente. Este middleware faz a API declarar quais
    # origens ela aceita. E uma permissao concedida pelo servidor, por isso a
    # lista e restrita e vem da configuracao, nunca "*".
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    app.include_router(health.router)

    return app


# Instancia usada pelo uvicorn: `uvicorn app.main:app`.
app = create_app()
