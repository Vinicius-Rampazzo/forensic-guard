"""Gravacao e remocao segura de evidencias temporarias.

O ForensicGuard nao guarda evidencia nenhuma. Todo arquivo enviado existe em
disco apenas enquanto esta sendo analisado, e some em seguida - inclusive
quando a analise falha no meio.

Tres regras de seguranca
------------------------
1. **O nome nunca vem do usuario.** Um upload chamado `..\\..\\Windows\\
   System32\\config.sys` nao pode virar caminho em disco. Geramos um UUID e
   descartamos o nome original para fins de gravacao - ele e preservado apenas
   como texto, para auditoria da extensao.

2. **A remocao acontece em `finally`.** Se o analisador levantar excecao, o
   arquivo tem que sumir do mesmo jeito. Uma ferramenta forense que deixa
   evidencia espalhada pelo disco contradiz a propria proposta.

3. **O limite de tamanho e verificado durante a escrita.** Confiar no
   cabecalho `Content-Length` nao serve: ele e informado pelo cliente e pode
   mentir. Esperar o arquivo inteiro chegar para so entao medir tambem nao -
   a essa altura o disco ja encheu.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO

from app.utils.streaming import read_chunks


class EvidenceTooLargeError(Exception):
    """O upload passou do limite configurado.

    Carrega o limite para que a camada HTTP possa informar ao usuario qual era
    o tamanho maximo aceito, em vez de um "arquivo grande demais" vago.
    """

    def __init__(self, limit_bytes: int) -> None:
        super().__init__(f"Evidence exceeds the maximum allowed size of {limit_bytes} bytes")
        self.limit_bytes = limit_bytes


@contextmanager
def temporary_evidence(directory: Path) -> Iterator[Path]:
    """Reserva um caminho temporario e garante que ele seja apagado.

    O caminho e devolvido antes de o arquivo existir: quem usa o context
    manager e responsavel por grava-lo. A remocao acontece de qualquer forma.

    Args:
        directory: pasta de trabalho. Criada se ainda nao existir.

    Yields:
        Caminho seguro, com nome gerado internamente.

    Example:
        >>> with temporary_evidence(Path("/tmp/forensicguard")) as path:
        ...     write_limited(upload, path, max_bytes=1024)
        ...     analyze(path)
        # aqui o arquivo ja nao existe mais
    """
    directory.mkdir(parents=True, exist_ok=True)

    # uuid4 e aleatorio, nao sequencial: dois uploads simultaneos nunca
    # colidem, e o nome nao revela nada sobre o conteudo nem sobre quantas
    # analises ja foram feitas.
    path = directory / uuid.uuid4().hex

    try:
        yield path
    finally:
        # missing_ok=True porque a gravacao pode ter falhado antes de criar o
        # arquivo - por exemplo, quando o upload estourou o limite. Nesse caso
        # nao ha nada a remover, e isso nao e erro.
        path.unlink(missing_ok=True)


def write_limited(source: BinaryIO, destination: Path, max_bytes: int) -> int:
    """Copia um fluxo para o disco, abortando se passar do limite.

    A verificacao acontece a cada bloco: assim que o acumulado ultrapassa o
    teto, a escrita para e o arquivo parcial e removido. O disco nunca recebe
    mais que `max_bytes` mais um bloco.

    Args:
        source: fluxo binario de origem, ja posicionado no inicio.
        destination: caminho de destino.
        max_bytes: tamanho maximo aceito.

    Returns:
        Quantos bytes foram gravados.

    Raises:
        EvidenceTooLargeError: quando a origem excede o limite.
    """
    written = 0

    try:
        with destination.open("wb") as target:
            for chunk in read_chunks(source):
                written += len(chunk)

                if written > max_bytes:
                    raise EvidenceTooLargeError(max_bytes)

                target.write(chunk)
    except EvidenceTooLargeError:
        # Remove o pedaco ja gravado antes de propagar. O context manager
        # tambem removeria, mas nao se pode contar com isso: esta funcao
        # precisa ser segura mesmo chamada sozinha.
        destination.unlink(missing_ok=True)
        raise

    return written
