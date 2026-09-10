"""Leitura de arquivos em blocos.

Por que este modulo existe
--------------------------
Ler um arquivo inteiro de uma vez e a armadilha mais cara desta aplicacao:

    data = path.read_bytes()   # um upload de 500 MB vira 500 MB de RAM

Como o ForensicGuard processa arquivos nao confiaveis por definicao, isso seria
um vetor de negacao de servico - bastariam alguns uploads grandes simultaneos
para esgotar a memoria do servidor.

Lendo em blocos, o consumo de memoria fica constante, independentemente do
tamanho da evidencia. Tanto o calculo de hashes quanto o de entropia precisam
percorrer todos os bytes, e ambos usam esta funcao: a logica de leitura fica
escrita uma vez so, e cada modulo cuida apenas do que faz com os bytes.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import BinaryIO

# Tamanho de cada leitura, em bytes.
#
# O valor equilibra dois custos: blocos grandes demais desperdicam memoria,
# blocos pequenos demais multiplicam as chamadas ao sistema operacional.
# 64 KiB e um meio-termo usado com frequencia para leitura sequencial.
CHUNK_SIZE = 64 * 1024


def read_chunks(stream: BinaryIO, chunk_size: int | None = None) -> Iterator[bytes]:
    """Percorre um fluxo binario devolvendo um bloco de cada vez.

    Args:
        stream: fluxo binario ja aberto.
        chunk_size: tamanho do bloco. Quando omitido, usa CHUNK_SIZE lido no
            momento da chamada - e nao um valor fixado na definicao da funcao,
            o que permite aos testes alterar o tamanho do bloco.

    Yields:
        Blocos de bytes, ate o fim do fluxo.
    """
    size = CHUNK_SIZE if chunk_size is None else chunk_size

    # iter(callable, sentinela) chama a funcao repetidamente ate ela devolver a
    # sentinela. Aqui: le blocos ate read() devolver b"", que sinaliza fim de
    # arquivo. E a forma idiomatica de escrever o laco "while True: chunk =
    # read(); if not chunk: break".
    yield from iter(lambda: stream.read(size), b"")
