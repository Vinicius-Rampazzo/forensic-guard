"""Rota de analise de evidencias.

Esta e a camada HTTP: ela recebe o upload, cuida de codigos de status e
delega. Nenhuma logica forense mora aqui.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.config import Settings, get_settings
from app.schemas.analysis import AnalysisResponse
from app.services.analysis_service import analyze_evidence
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
