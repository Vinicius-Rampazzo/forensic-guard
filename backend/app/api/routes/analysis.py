"""Rota de analise de evidencias.

Esta e a camada HTTP: ela recebe o upload, cuida de codigos de status e
delega. Nenhuma logica forense mora aqui.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from app.config import Settings, get_settings
from app.schemas.analysis import AnalysisResponse
from app.schemas.url_analysis import UrlAnalysisResponse, UrlResolutionResponse
from app.services.analysis_service import analyze_evidence
from app.services.url_service import analyze_url_evidence, resolve_url_destination
from app.utils.temporary_files import (
    EvidenceTooLargeError,
    temporary_evidence,
    write_limited,
)

router = APIRouter(tags=["analysis"])

# Nome usado quando o cliente envia um arquivo sem informar nome algum.
# Nao e um default inofensivo por acaso: sem extensao, a regra de mismatch
# nao tem o que contradizer e nao produz falso positivo.
FALLBACK_FILENAME = "unnamed"


@router.post(
    "/analyze",
    response_model=AnalysisResponse,
    summary="Analyse a piece of digital evidence",
    responses={
        413: {"description": "The uploaded file exceeds the configured size limit"},
    },
)
def analyze(
    settings: Annotated[Settings, Depends(get_settings)],
    file: Annotated[UploadFile, File(description="The evidence to analyse")],
) -> AnalysisResponse:
    """Recebe um arquivo, analisa e devolve o resultado.

    A evidencia e gravada num temporario com nome gerado internamente, lida em
    blocos e apagada ao final - inclusive se a analise levantar excecao. Nada
    e persistido.

    Por que `def` e nao `async def`
    -------------------------------
    Esta funcao faz trabalho bloqueante: le disco e calcula hashes. Numa rota
    `async def`, isso travaria o laco de eventos, e o servidor inteiro pararia
    de responder enquanto um arquivo grande fosse processado - inclusive o
    /health.

    Declarada como `def`, o FastAPI a executa num pool de threads
    automaticamente, e o laco de eventos continua livre. E o erro mais comum
    de quem comeca com FastAPI: marcar tudo como `async` achando que fica mais
    rapido, e conseguir o oposto.
    """
    original_filename = file.filename or FALLBACK_FILENAME

    with temporary_evidence(settings.temp_dir) as path:
        try:
            # `file.file` e o fluxo binario por tras do upload. A escrita e
            # feita em blocos, com o limite verificado a cada um deles - nunca
            # confiando no cabecalho Content-Length, que o cliente controla.
            write_limited(file.file, path, max_bytes=settings.max_upload_size)
        except EvidenceTooLargeError as error:
            raise HTTPException(
                # 413 Content Too Large. O nome antigo da constante
                # (REQUEST_ENTITY_TOO_LARGE) foi depreciado pelo Starlette.
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=(
                    f"Evidence exceeds the maximum allowed size of "
                    f"{error.limit_bytes} bytes"
                ),
            ) from error

        return analyze_evidence(path, original_filename=original_filename)


class UrlRequest(BaseModel):
    """Corpo de POST /analyze/url."""

    url: str = Field(
        min_length=1,
        max_length=4096,
        description="The address to inspect. It is never visited.",
    )


@router.post(
    "/analyze/url",
    response_model=UrlAnalysisResponse,
    summary="Analyse a URL without visiting it",
)
def analyze_url_endpoint(request: UrlRequest) -> UrlAnalysisResponse:
    """Disseca uma URL e aponta as caracteristicas incomuns.

    Nenhuma requisicao e feita ao endereco - nem DNS, nem certificado, nem a
    pagina. Infraestrutura de phishing registra cada acesso, e consultar uma
    URL suspeita avisa a quem a montou que ela esta sendo investigada.

    Rota sincrona e rapida: a analise e puramente estrutural, sem disco e sem
    rede. Mesmo assim fica como `def`, e nao `async def`, por consistencia com
    o restante da API - e porque o FastAPI a executa num pool de threads, o
    que mantem o laco de eventos livre.

    O limite de 4096 caracteres existe porque todo campo de texto aceito pela
    API precisa de teto. URLs reais raramente passam de 2000.
    """
    return analyze_url_evidence(request.url)


@router.post(
    "/analyze/url/resolve",
    response_model=UrlResolutionResponse,
    summary="Follow a URL's redirects and analyse where it lands",
)
def resolve_url_endpoint(request: UrlRequest) -> UrlResolutionResponse:
    """Segue os redirecionamentos e analisa o destino final.

    Esta rota CONTACTA o endereco. E a unica do sistema que faz isso, e por
    isso ela existe separada de `/analyze/url` em vez de ser um parametro
    dela: um booleano no corpo da requisicao esconderia, atras de um valor
    padrao, a diferenca entre nao tocar na rede e tocar.

    Quem chama precisa saber tres coisas, e todas estao no `disclaimer` da
    resposta:

    1. a requisicao avisa a quem montou o link que ele foi aberto;
    2. o resultado e para onde ESTE servidor foi mandado, neste instante - um
       redirecionador pode servir destinos diferentes conforme quem pergunta;
    3. cada salto e verificado contra enderecos de rede interna antes de ser
       seguido, porque seguir redirecionamento de terceiro e, por definicao,
       deixar outra pessoa escolher o que o servidor vai acessar.
    """
    return resolve_url_destination(request.url)
