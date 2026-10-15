"""Testes da gravacao e remocao de evidencias temporarias.

Estes sao os testes de maior consequencia do projeto. Um defeito aqui nao
aparece na tela: ele se manifesta como arquivo suspeito acumulando em disco, ou
como disco cheio depois de alguns uploads grandes.
"""

import io
from pathlib import Path

import pytest

from app.utils import streaming
from app.utils.temporary_files import (
    EvidenceTooLargeError,
    temporary_evidence,
    write_limited,
)


class TestTemporaryPath:
    """Reserva do caminho temporario."""

    def test_creates_the_directory_when_missing(self, tmp_path: Path) -> None:
        """A pasta de trabalho nasce sozinha no primeiro uso."""
        workdir = tmp_path / "forensicguard" / "nested"

        with temporary_evidence(workdir) as path:
            assert workdir.is_dir()
            assert path.parent == workdir

    def test_generated_names_are_unique(self, tmp_path: Path) -> None:
        """Dois uploads simultaneos nunca colidem.

        Nome sequencial causaria colisao sob concorrencia e ainda revelaria
        quantas analises ja foram feitas.
        """
        with temporary_evidence(tmp_path) as first, temporary_evidence(tmp_path) as second:
            assert first != second

    def test_name_does_not_come_from_the_user(self, tmp_path: Path) -> None:
        """O nome e um UUID em hexadecimal, sem extensao e sem relacao com o upload."""
        with temporary_evidence(tmp_path) as path:
            assert len(path.name) == 32
            assert all(character in "0123456789abcdef" for character in path.name)


class TestCleanup:
    """Remocao do temporario - a parte que nao pode falhar."""

    def test_removes_the_file_on_the_happy_path(self, tmp_path: Path) -> None:
        with temporary_evidence(tmp_path) as path:
            path.write_bytes(b"evidencia")
            assert path.exists()

        assert not path.exists()

    def test_removes_the_file_even_when_the_analysis_raises(self, tmp_path: Path) -> None:
        """O teste mais importante do modulo.

        Se o analisador explodir no meio - parser hostil, arquivo corrompido,
        bug nosso - a evidencia tem que sumir do mesmo jeito. Uma ferramenta
        forense que deixa arquivo suspeito espalhado contradiz a propria
        proposta de nao persistir nada.
        """
        leaked: Path | None = None

        with pytest.raises(RuntimeError):
            with temporary_evidence(tmp_path) as path:
                leaked = path
                path.write_bytes(b"evidencia")
                raise RuntimeError("o analisador falhou")

        assert leaked is not None
        assert not leaked.exists()

    def test_does_not_fail_when_the_file_was_never_created(self, tmp_path: Path) -> None:
        """Nada a remover nao e erro.

        Acontece quando o upload estoura o limite antes de qualquer escrita.
        """
        with temporary_evidence(tmp_path) as path:
            assert not path.exists()

    def test_leaves_the_working_directory_empty(self, tmp_path: Path) -> None:
        """Depois de varias analises, nenhum residuo fica para tras."""
        for _ in range(5):
            with temporary_evidence(tmp_path) as path:
                path.write_bytes(b"evidencia")

        assert list(tmp_path.iterdir()) == []


class TestSizeLimit:
    """Aplicacao do limite de tamanho durante a escrita."""

    def test_writes_content_within_the_limit(self, tmp_path: Path) -> None:
        destination = tmp_path / "evidence.bin"
        payload = b"forensicguard" * 10

        written = write_limited(io.BytesIO(payload), destination, max_bytes=1024)

        assert written == len(payload)
        assert destination.read_bytes() == payload

    def test_accepts_content_exactly_at_the_limit(self, tmp_path: Path) -> None:
        """Caso de fronteira: no limite ainda e aceito."""
        destination = tmp_path / "exact.bin"
        payload = b"A" * 100

        assert write_limited(io.BytesIO(payload), destination, max_bytes=100) == 100

    def test_rejects_content_one_byte_over_the_limit(self, tmp_path: Path) -> None:
        destination = tmp_path / "over.bin"

        with pytest.raises(EvidenceTooLargeError):
            write_limited(io.BytesIO(b"A" * 101), destination, max_bytes=100)

    def test_removes_the_partial_file_when_the_limit_is_exceeded(self, tmp_path: Path) -> None:
        """O pedaco ja gravado nao fica para tras.

        Sem isso, um atacante encheria o disco mandando uploads grandes de
        proposito: cada um deixaria para tras o tanto que coube antes do corte.
        """
        destination = tmp_path / "partial.bin"

        with pytest.raises(EvidenceTooLargeError):
            write_limited(io.BytesIO(b"A" * 100_000), destination, max_bytes=1024)

        assert not destination.exists()

    def test_the_error_carries_the_limit(self, tmp_path: Path) -> None:
        """A camada HTTP precisa informar qual era o tamanho maximo aceito."""
        with pytest.raises(EvidenceTooLargeError) as raised:
            write_limited(io.BytesIO(b"A" * 50), tmp_path / "x.bin", max_bytes=10)

        assert raised.value.limit_bytes == 10

    def test_stops_reading_as_soon_as_the_limit_is_passed(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """A verificacao e por bloco, nao no final.

        Esperar o arquivo inteiro chegar para so entao medir seria inutil: a
        essa altura o disco ja recebeu tudo. Com bloco de 10 bytes e limite de
        10, a escrita para no segundo bloco - muito antes dos 10.000 bytes.
        """
        monkeypatch.setattr(streaming, "CHUNK_SIZE", 10)
        source = io.BytesIO(b"A" * 10_000)

        with pytest.raises(EvidenceTooLargeError):
            write_limited(source, tmp_path / "huge.bin", max_bytes=10)

        # Leu apenas os dois primeiros blocos antes de abortar.
        assert source.tell() == 20

    def test_empty_upload_is_allowed(self, tmp_path: Path) -> None:
        """Arquivo vazio e evidencia valida, nao erro."""
        destination = tmp_path / "empty.bin"

        assert write_limited(io.BytesIO(b""), destination, max_bytes=1024) == 0
        assert destination.read_bytes() == b""
