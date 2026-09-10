"""Testes da leitura em blocos.

Modulo pequeno, mas e a base de todo o resto: se ele perder bytes, hashes e
entropia ficam errados em silencio.
"""

import io

from app.utils import streaming
from app.utils.streaming import read_chunks


class TestChunkIntegrity:
    """Os blocos, juntos, reproduzem exatamente o conteudo original."""

    def test_rejoined_chunks_match_the_original(self) -> None:
        """Nenhum byte se perde nem se duplica entre os blocos."""
        payload = bytes(range(256)) * 40

        chunks = list(read_chunks(io.BytesIO(payload), chunk_size=7))

        assert b"".join(chunks) == payload

    def test_every_chunk_has_the_requested_size_except_the_last(self) -> None:
        """O ultimo bloco carrega apenas o resto que sobrou."""
        payload = b"a" * 25

        chunks = list(read_chunks(io.BytesIO(payload), chunk_size=10))

        assert [len(chunk) for chunk in chunks] == [10, 10, 5]

    def test_empty_stream_yields_no_chunk(self) -> None:
        """Fluxo vazio nao produz bloco algum - nem um bloco vazio."""
        assert list(read_chunks(io.BytesIO(b""))) == []


class TestChunkSizeConfiguration:
    """O tamanho do bloco pode ser alterado, inclusive pelos testes."""

    def test_falls_back_to_the_module_default(self, monkeypatch) -> None:
        """O padrao e lido na chamada, nao fixado na definicao da funcao.

        E isso que permite aos testes alterarem o tamanho do bloco. Se o valor
        fosse um argumento default comum (chunk_size=CHUNK_SIZE), ele teria
        sido congelado quando o modulo foi importado, e este teste falharia.
        """
        monkeypatch.setattr(streaming, "CHUNK_SIZE", 4)

        chunks = list(read_chunks(io.BytesIO(b"abcdefghij")))

        assert [len(chunk) for chunk in chunks] == [4, 4, 2]


class TestLazyEvaluation:
    """A leitura acontece sob demanda, e nao toda de uma vez."""

    def test_nothing_is_read_before_the_first_iteration(self) -> None:
        """A funcao devolve um gerador, nao uma lista pronta.

        Importa para o consumo de memoria: se ela montasse a lista de todos os
        blocos antes de devolver, o arquivo inteiro estaria em memoria de novo
        - e o proposito do modulo seria anulado.
        """
        stream = io.BytesIO(b"abcdef")
        chunks = read_chunks(stream, chunk_size=2)

        # Nada foi lido ainda: a posicao do fluxo continua no inicio.
        assert stream.tell() == 0

        next(chunks)

        assert stream.tell() == 2
