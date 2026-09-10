"""Testes do calculo de hashes.

Os valores esperados sao vetores de teste publicados (NIST / RFC), digitados
aqui como constantes. Isso e proposital: se o teste calculasse o esperado
chamando a propria hashlib, ele passaria mesmo com a leitura em blocos
quebrada, porque os dois lados usariam o mesmo caminho defeituoso. Comparar com
um valor externo e o que da sentido ao teste.
"""

import io
from pathlib import Path

import pytest

from app.utils import streaming
from app.utils.hashing import compute_hashes, compute_hashes_from_stream

# Vetores de teste para a entrada b"abc"
ABC_HASHES = {
    "md5": "900150983cd24fb0d6963f7d28e17f72",
    "sha1": "a9993e364706816aba3e25717850c26c9cd0d89d",
    "sha256": "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
    "sha512": (
        "ddaf35a193617abacc417349ae20413112e6fa4e89a97ea20a9eeee64b55d39a"
        "2192992a274fc1a836ba3c23a3feebbd454d4423643ce80e2a9ac94fa54ca49f"
    ),
}

# Vetores de teste para a entrada vazia
EMPTY_HASHES = {
    "md5": "d41d8cd98f00b204e9800998ecf8427e",
    "sha1": "da39a3ee5e6b4b0d3255bfef95601890afd80709",
    "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
}


class TestKnownVectors:
    """Os resultados batem com valores publicados externamente."""

    def test_matches_the_published_vectors_for_abc(self, tmp_path: Path) -> None:
        """Os quatro algoritmos produzem os hashes conhecidos de b"abc"."""
        evidence = tmp_path / "abc.bin"
        evidence.write_bytes(b"abc")

        assert compute_hashes(evidence) == ABC_HASHES

    def test_matches_the_published_vectors_for_an_empty_file(self, tmp_path: Path) -> None:
        """Arquivo vazio tem hash valido e conhecido - nao e caso de erro."""
        evidence = tmp_path / "empty.bin"
        evidence.write_bytes(b"")

        result = compute_hashes(evidence, algorithms=("md5", "sha1", "sha256"))

        assert result == EMPTY_HASHES


class TestChunkedReading:
    """A leitura incremental nao altera o resultado."""

    def test_a_tiny_chunk_size_produces_the_same_hashes(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """O resultado nao depende do tamanho do bloco de leitura.

        Este e o teste que realmente protege a decisao de arquitetura do
        modulo. Ele forca um bloco minusculo (3 bytes), obrigando muitas
        iteracoes, e exige o mesmo hash de sempre. Se alguem trocar a leitura
        incremental por algo que perca bytes entre os blocos, ou que reinicie o
        hash a cada bloco, este teste falha.
        """
        evidence = tmp_path / "chunked.bin"
        payload = b"forensicguard" * 500
        evidence.write_bytes(payload)

        expected = compute_hashes_from_stream(io.BytesIO(payload))

        monkeypatch.setattr(streaming, "CHUNK_SIZE", 3)

        assert compute_hashes(evidence) == expected

    def test_content_larger_than_one_chunk_is_hashed_consistently(self, tmp_path: Path) -> None:
        """Arquivo e fluxo em memoria produzem o mesmo resultado."""
        evidence = tmp_path / "large.bin"
        payload = b"forensicguard" * 100_000  # ~1.3 MB, bem acima do CHUNK_SIZE
        evidence.write_bytes(payload)

        from_file = compute_hashes(evidence)
        from_stream = compute_hashes_from_stream(io.BytesIO(payload))

        assert from_file == from_stream
        # Um hash SHA-256 tem 256 bits, ou seja, 64 caracteres hexadecimais.
        assert len(from_file["sha256"]) == 64


class TestOutputFormat:
    """O formato do resultado e estavel e previsivel."""

    def test_accepts_a_subset_of_algorithms(self, tmp_path: Path) -> None:
        """E possivel pedir apenas alguns algoritmos."""
        evidence = tmp_path / "subset.bin"
        evidence.write_bytes(b"abc")

        result = compute_hashes(evidence, algorithms=("sha256",))

        assert result == {"sha256": ABC_HASHES["sha256"]}

    def test_digests_are_lowercase_hexadecimal(self, tmp_path: Path) -> None:
        """Importa porque comparacao com listas de indicadores e textual.

        "ABC123" nao e igual a "abc123" para o operador ==, e um hash exibido
        em caixa alta nao casaria com uma base de IOCs em caixa baixa.
        """
        evidence = tmp_path / "case.bin"
        evidence.write_bytes(b"abc")

        for digest in compute_hashes(evidence).values():
            assert digest == digest.lower()
            assert all(character in "0123456789abcdef" for character in digest)


class TestErrorHandling:
    """Falhas sao explicitas, nunca silenciosas."""

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        """Arquivo inexistente falha de forma clara, sem devolver hash vazio."""
        with pytest.raises(FileNotFoundError):
            compute_hashes(tmp_path / "does-not-exist.bin")

    def test_unknown_algorithm_raises(self, tmp_path: Path) -> None:
        """Algoritmo desconhecido falha em vez de ser ignorado em silencio."""
        evidence = tmp_path / "algo.bin"
        evidence.write_bytes(b"abc")

        with pytest.raises(ValueError):
            compute_hashes(evidence, algorithms=("not-a-real-algorithm",))
