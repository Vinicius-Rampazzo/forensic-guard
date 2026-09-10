"""Testes do calculo de entropia.

A entropia tem valores extremos que podem ser deduzidos matematicamente, sem
depender da implementacao. Sao esses os casos testados aqui - eles ancoram a
formula em verdades independentes do codigo.
"""

import io
from pathlib import Path

from app.utils import streaming
from app.utils.entropy import (
    MAX_ENTROPY,
    compute_entropy,
    compute_entropy_from_stream,
)


class TestMathematicalExtremes:
    """Casos cujo resultado pode ser deduzido no papel, sem rodar o codigo."""

    def test_empty_file_has_zero_entropy(self, tmp_path: Path) -> None:
        """Sem byte nenhum nao ha imprevisibilidade.

        Tambem garante que a formula nao tenta dividir por zero.
        """
        evidence = tmp_path / "empty.bin"
        evidence.write_bytes(b"")

        assert compute_entropy(evidence) == 0.0

    def test_a_single_repeated_byte_has_zero_entropy(self, tmp_path: Path) -> None:
        """Um unico valor repetido e totalmente previsivel.

        Com um so valor, p = 1 e log2(1) = 0, entao o somatorio inteiro zera.
        """
        evidence = tmp_path / "zeros.bin"
        evidence.write_bytes(b"\x00" * 10_000)

        assert compute_entropy(evidence) == 0.0

    def test_two_equally_likely_values_give_exactly_one_bit(self, tmp_path: Path) -> None:
        """E o caso do cara ou coroa.

        Uma resposta binaria equilibrada carrega exatamente um bit de
        informacao.
        """
        evidence = tmp_path / "binary.bin"
        evidence.write_bytes(b"\x00\xff" * 5_000)

        assert compute_entropy(evidence) == 1.0

    def test_all_byte_values_evenly_distributed_reach_the_maximum(self, tmp_path: Path) -> None:
        """Os 256 valores igualmente distribuidos dao exatamente 8.0.

        E o limite superior da escala: com 256 possibilidades equiprovaveis,
        cada byte carrega log2(256) = 8 bits. Nenhum arquivo real chega aqui,
        mas o caso construido prova que a formula esta correta no extremo.
        """
        evidence = tmp_path / "uniform.bin"
        evidence.write_bytes(bytes(range(256)) * 100)

        assert compute_entropy(evidence) == MAX_ENTROPY


class TestRealContent:
    """Comportamento com conteudo parecido com o do mundo real."""

    def test_result_stays_within_the_scale(self, tmp_path: Path) -> None:
        """Qualquer conteudo produz um valor entre 0 e 8."""
        evidence = tmp_path / "text.bin"
        evidence.write_bytes(b"ForensicGuard analisa evidencias digitais. " * 200)

        entropy = compute_entropy(evidence)

        assert 0.0 <= entropy <= MAX_ENTROPY

    def test_text_has_lower_entropy_than_unstructured_data(self) -> None:
        """Texto natural e mais previsivel que dados sem padrao.

        Este teste expressa o conceito que justifica o indicador de entropia
        alta: estrutura e repeticao derrubam o valor; ausencia de padrao o
        eleva.

        Os dados "aleatorios" sao gerados de forma deterministica para que o
        teste nunca falhe por azar do sorteio.
        """
        text = b"forensic evidence analysis report " * 300

        # Sequencia pseudoaleatoria simples e reprodutivel: percorre os 256
        # valores com um passo primo, o que os distribui uniformemente.
        pseudo_random = bytes((index * 167) % 256 for index in range(10_000))

        text_entropy = compute_entropy_from_stream(io.BytesIO(text))
        random_entropy = compute_entropy_from_stream(io.BytesIO(pseudo_random))

        assert text_entropy < random_entropy
        assert random_entropy > 7.5


class TestChunkedReading:
    """A contagem de frequencias sobrevive a leitura em blocos."""

    def test_a_tiny_chunk_size_produces_the_same_entropy(self, monkeypatch) -> None:
        """A tabela de frequencias nao se perde entre os blocos.

        Um bloco de 3 bytes obriga milhares de iteracoes sobre o mesmo
        conteudo. Se a tabela fosse reiniciada a cada bloco - erro facil de
        cometer - o resultado mudaria.
        """
        payload = b"ForensicGuard" * 1_000

        expected = compute_entropy_from_stream(io.BytesIO(payload))

        monkeypatch.setattr(streaming, "CHUNK_SIZE", 3)
        result = compute_entropy_from_stream(io.BytesIO(payload))

        assert result == expected
