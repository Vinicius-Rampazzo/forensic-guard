"""Calculo de hashes criptograficos de evidencias.

Um hash e uma impressao digital do arquivo: qualquer bit alterado produz um
valor completamente diferente. Em forense ele serve para tres coisas:

1. **identificar** a evidencia sem revelar o conteudo dela;
2. **comparar** com listas publicas de indicadores (IOCs) e bases como o NSRL;
3. **provar integridade** - o mesmo arquivo sempre produz o mesmo hash.

Por que quatro algoritmos
-------------------------
MD5 e SHA-1 estao quebrados para uso criptografico: existem tecnicas praticas
para fabricar dois arquivos diferentes com o mesmo hash (colisao). Ainda assim
eles continuam aqui, porque a maioria das bases de indicadores e dos relatorios
de antivirus publica MD5 - sem ele nao ha como cruzar informacao.

A regra do projeto: **MD5 e SHA-1 servem para procurar, nunca para confiar.**
O SHA-256 e o identificador principal exibido ao usuario.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import BinaryIO

from app.utils.streaming import read_chunks

# Ordem em que os algoritmos aparecem no resultado.
DEFAULT_ALGORITHMS = ("md5", "sha1", "sha256", "sha512")


def compute_hashes(
    path: Path,
    algorithms: tuple[str, ...] = DEFAULT_ALGORITHMS,
) -> dict[str, str]:
    """Calcula os hashes de um arquivo.

    Args:
        path: caminho do arquivo a ser lido.
        algorithms: nomes reconhecidos pela hashlib.

    Returns:
        Dicionario do nome do algoritmo para o hash em hexadecimal minusculo.

    Raises:
        FileNotFoundError: se o caminho nao existir.
        ValueError: se algum algoritmo nao for reconhecido pela hashlib.
    """
    with path.open("rb") as stream:
        return compute_hashes_from_stream(stream, algorithms)


def compute_hashes_from_stream(
    stream: BinaryIO,
    algorithms: tuple[str, ...] = DEFAULT_ALGORITHMS,
) -> dict[str, str]:
    """Calcula os hashes de um fluxo binario ja aberto.

    Existe separada de compute_hashes por dois motivos praticos: os testes
    podem usar io.BytesIO em vez de criar arquivo em disco, e a analise de
    anexos de e-mail (que chegam em memoria) podera reaproveitar esta funcao
    sem precisar gravar nada.
    """
    hashers = {name: _new_hasher(name) for name in algorithms}

    for chunk in read_chunks(stream):
        for hasher in hashers.values():
            # Todos os algoritmos consomem o MESMO bloco. Por isso os quatro
            # hashes custam uma unica leitura do disco.
            hasher.update(chunk)

    return {name: hasher.hexdigest() for name, hasher in hashers.items()}


def _new_hasher(algorithm: str) -> hashlib._Hash:
    """Cria um objeto de hash tolerante a sistemas em modo FIPS.

    Em sistemas configurados com FIPS, a hashlib recusa criar MD5, porque o
    algoritmo nao e considerado seguro. O parametro usedforsecurity=False
    declara que este MD5 e usado como identificador, nao como protecao
    criptografica - e a hashlib entao permite.

    Sem isso, o ForensicGuard quebraria em ambientes corporativos e de governo,
    justamente onde uma ferramenta forense tende a ser usada.
    """
    try:
        return hashlib.new(algorithm, usedforsecurity=False)
    except TypeError:
        # Implementacoes alternativas de Python podem nao aceitar o parametro.
        return hashlib.new(algorithm)
