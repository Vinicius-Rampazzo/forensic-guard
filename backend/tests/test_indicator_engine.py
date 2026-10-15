"""Testes da extracao de indicadores.

A medida de qualidade aqui nao e "achou o indicador". E "nao gritou a toa":
boa parte dos testes abaixo verifica casos em que NENHUM indicador deve ser
emitido. Uma ferramenta de triagem que alerta sobre tudo ensina o usuario a
ignorar os alertas.
"""

from pathlib import Path

from app.analyzers.file_analyzer import analyze_file
from app.analyzers.image_analyzer import GpsCoordinates, ImageAnalysis
from app.services.evidence_detector import detect_evidence
from app.services.indicator_engine import _image_indicators, collect_indicators

PADDING = b"\x00" * 64

PNG = b"\x89PNG\r\n\x1a\n" + PADDING
ZIP = b"PK\x03\x04\x14\x00\x00\x00" + PADDING
PLAIN_TEXT = b"Relatorio trimestral de vendas. Nada de especial aqui.\n" * 10

FAKE_DROPPER = (
    b"MZ\x90\x00\x03\x00\x00\x00"
    b"powershell.exe -windowstyle hidden -EncodedCommand payload\x00"
    b"https://malicious.example.com/stage2.exe\x00"
)

# Conteudo com entropia proxima do maximo, sem assinatura reconhecivel.
# Gerado de forma deterministica para o teste nunca falhar por sorteio.
HIGH_ENTROPY = bytes((index * 167) % 256 for index in range(20_000))


def indicator_ids(tmp_path: Path, name: str, content: bytes) -> list[str]:
    """Grava a fixture, analisa e devolve os ids dos indicadores emitidos."""
    evidence = tmp_path / name
    evidence.write_bytes(content)

    analysis = analyze_file(evidence)
    detection = detect_evidence(evidence)

    return [item.rule.id for item in collect_indicators(analysis, detection)]


class TestMismatchIndicators:
    """Indicadores derivados da contradicao entre nome e conteudo."""

    def test_disguised_executable_raises_both_rules(self, tmp_path: Path) -> None:
        """Dois indicadores para o mesmo fato, e isso e proposital.

        O arquivo E um mismatch de extensao (35) E um executavel disfarcado
        (50). Somados dao 85 - a faixa CRITICAL documentada na especificacao.
        Cada um aparece no relatorio com sua propria explicacao.
        """
        ids = indicator_ids(tmp_path, "invoice.jpg", FAKE_DROPPER)

        assert "file.extension_mismatch" in ids
        assert "file.executable_disguised" in ids

    def test_plain_mismatch_raises_only_the_generic_rule(self, tmp_path: Path) -> None:
        """Um PNG chamado .pdf e nome errado, nao entrega de malware."""
        ids = indicator_ids(tmp_path, "documento.pdf", PNG)

        assert "file.extension_mismatch" in ids
        assert "file.executable_disguised" not in ids

    def test_correct_extension_raises_nothing(self, tmp_path: Path) -> None:
        assert indicator_ids(tmp_path, "grafico.png", PNG) == []

    def test_container_format_raises_nothing(self, tmp_path: Path) -> None:
        """Um .docx E um ZIP por dentro - detectar isso nao e achado."""
        assert indicator_ids(tmp_path, "contrato.docx", ZIP) == []

    def test_unknown_format_raises_nothing(self, tmp_path: Path) -> None:
        """Texto comum nao tem assinatura, e isso nunca e suspeito."""
        assert indicator_ids(tmp_path, "notas.txt", PLAIN_TEXT) == []


class TestEntropyIndicator:
    """Entropia alta so vira indicador quando e inesperada para o formato."""

    def test_raises_for_high_entropy_in_an_unknown_format(self, tmp_path: Path) -> None:
        ids = indicator_ids(tmp_path, "dados.bin", HIGH_ENTROPY)

        assert "file.unexpected_entropy" in ids

    def test_does_not_raise_for_naturally_compressed_formats(self, tmp_path: Path) -> None:
        """O teste que impede a ferramenta de gritar em toda foto.

        Um ZIP legitimo tem entropia perto de 8 por construcao. Emitir o
        indicador nele encheria o relatorio de ruido e destruiria a
        credibilidade do score.
        """
        compressed = b"PK\x03\x04\x14\x00\x00\x00" + HIGH_ENTROPY

        ids = indicator_ids(tmp_path, "arquivo.zip", compressed)

        assert "file.unexpected_entropy" not in ids

    def test_does_not_raise_for_ordinary_text(self, tmp_path: Path) -> None:
        """Texto natural fica perto de 4.5 - bem abaixo do limite."""
        ids = indicator_ids(tmp_path, "notas.txt", PLAIN_TEXT)

        assert "file.unexpected_entropy" not in ids


class TestStringIndicators:
    """Referencias a interpretadores e tecnicas de execucao."""

    def test_raises_for_command_interpreter_references(self, tmp_path: Path) -> None:
        ids = indicator_ids(tmp_path, "dropper.bin", FAKE_DROPPER)

        assert "strings.suspicious_command" in ids

    def test_does_not_raise_for_ordinary_content(self, tmp_path: Path) -> None:
        ids = indicator_ids(tmp_path, "notas.txt", PLAIN_TEXT)

        assert "strings.suspicious_command" not in ids


class TestUrlIndicators:
    """Heuristicas sobre as URLs encontradas no conteudo."""

    def test_raises_for_a_url_pointing_to_an_ip_address(self, tmp_path: Path) -> None:
        content = b"baixa de http://203.0.113.45/payload.bin agora\x00" + PADDING

        ids = indicator_ids(tmp_path, "amostra.bin", content)

        assert "url.ip_address_host" in ids

    def test_raises_for_a_punycode_domain(self, tmp_path: Path) -> None:
        content = b"acesse https://xn--80ak6aa92e.com/login agora\x00" + PADDING

        ids = indicator_ids(tmp_path, "amostra.bin", content)

        assert "url.punycode_domain" in ids

    def test_does_not_raise_for_an_ordinary_url(self, tmp_path: Path) -> None:
        content = b"documentacao em https://docs.python.org/3/library/\x00" + PADDING

        ids = indicator_ids(tmp_path, "amostra.bin", content)

        assert "url.ip_address_host" not in ids
        assert "url.punycode_domain" not in ids


class TestImageIndicators:
    """Indicadores especificos de imagem."""

    def test_gps_raises_an_informational_indicator(self) -> None:
        """Localizacao embutida avisa, nao acusa.

        Pontua zero de proposito: a foto nao fica perigosa por saber onde foi
        tirada. Quem fica exposto e quem a enviou.
        """
        image = ImageAnalysis(width=64, height=48, gps=GpsCoordinates(-22.12, -51.39))

        indicators = _image_indicators(image, file_size=1024)

        assert len(indicators) == 1
        assert indicators[0].rule.id == "image.gps_coordinates"
        assert indicators[0].rule.score == 0
        assert indicators[0].evidence["latitude"] == -22.12

    def test_decompression_bomb_raises_a_scored_indicator(self) -> None:
        image = ImageAnalysis(decompression_bomb=True, error="too many pixels")

        indicators = _image_indicators(image, file_size=68)

        assert indicators[0].rule.id == "image.decompression_bomb"
        assert indicators[0].rule.score > 0

    def test_bomb_evidence_is_useful_even_without_dimensions(self) -> None:
        """Quando a protecao aborta na abertura, as dimensoes nao chegam.

        A evidencia precisa dizer algo util mesmo assim: a desproporcao entre
        68 bytes e o limite de pixels ja conta a historia.
        """
        image = ImageAnalysis(decompression_bomb=True)

        evidence = _image_indicators(image, file_size=68)[0].evidence

        assert evidence["file_size_bytes"] == 68
        assert evidence["pixel_limit"] > 0
        assert "declared_width" not in evidence

    def test_bomb_evidence_includes_dimensions_when_known(self) -> None:
        image = ImageAnalysis(width=60_000, height=60_000, decompression_bomb=True)

        evidence = _image_indicators(image, file_size=1024)[0].evidence

        assert evidence["declared_width"] == 60_000
        assert evidence["declared_megapixels"] == 3600.0

    def test_an_ordinary_photo_raises_nothing(self) -> None:
        """Nem EXIF ausente nem software de edicao viram indicador."""
        image = ImageAnalysis(
            width=4032,
            height=3024,
            image_format="JPEG",
            software="Adobe Photoshop 25.1",
        )

        assert _image_indicators(image, file_size=191_388) == []

    def test_non_image_evidence_raises_nothing(self) -> None:
        assert _image_indicators(None, file_size=1024) == []


class TestEvidenceIsAlwaysPresent:
    """A regra que sustenta a explicabilidade do score."""

    def test_every_indicator_carries_its_evidence(self, tmp_path: Path) -> None:
        """Indicador sem evidencia e opiniao, nao observacao.

        Quem le o relatorio precisa conseguir conferir a conclusao sozinho - e
        discordar dela, se for o caso.
        """
        evidence_file = tmp_path / "invoice.jpg"
        evidence_file.write_bytes(FAKE_DROPPER)

        indicators = collect_indicators(
            analyze_file(evidence_file),
            detect_evidence(evidence_file),
        )

        assert indicators

        for item in indicators:
            # O aviso de truncamento e o unico que pode vir sem dados, porque
            # ele fala sobre a analise e nao sobre o arquivo.
            if item.rule.id == "analysis.truncated":
                continue

            assert item.evidence, item.rule.id

    def test_mismatch_evidence_names_both_sides_of_the_contradiction(
        self, tmp_path: Path
    ) -> None:
        """A evidencia precisa mostrar o que foi declarado E o que foi achado."""
        evidence_file = tmp_path / "invoice.jpg"
        evidence_file.write_bytes(FAKE_DROPPER)

        indicators = collect_indicators(
            analyze_file(evidence_file),
            detect_evidence(evidence_file),
        )

        mismatch = next(item for item in indicators if item.rule.id == "file.extension_mismatch")

        assert mismatch.evidence["declared_extension"] == ".jpg"
        assert "Windows executable" in mismatch.evidence["detected_type"]
