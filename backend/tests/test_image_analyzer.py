"""Testes da analise de imagem.

As imagens de teste sao geradas pelo proprio Pillow, com EXIF e GPS escritos
por codigo. Nenhum binario entra no repositorio, e as fixtures ficam legiveis:
da para ver no teste exatamente qual metadado foi gravado.
"""

import struct
import zlib
from pathlib import Path

import pytest
from PIL import ExifTags, Image
from PIL.TiffImagePlugin import IFDRational

from app.analyzers.image_analyzer import MAX_SAFE_PIXELS, analyze_image


def write_image(
    path: Path,
    size: tuple[int, int] = (64, 48),
    image_format: str = "JPEG",
    **exif_values: str,
) -> Path:
    """Gera uma imagem com os metadados EXIF informados."""
    image = Image.new("RGB", size, (10, 20, 30))

    if not exif_values:
        # O Pillow nao aceita exif=None: o argumento precisa ser OMITIDO
        # quando nao ha metadado a gravar.
        image.save(path, format=image_format)
        return path

    exif = image.getexif()

    for name, value in exif_values.items():
        exif[ExifTags.Base[name].value] = value

    image.save(path, format=image_format, exif=exif)
    return path


def write_image_with_gps(
    path: Path,
    latitude: tuple[int, int, int],
    latitude_ref: str,
    longitude: tuple[int, int, int],
    longitude_ref: str,
) -> Path:
    """Gera um JPEG com coordenadas GPS em graus, minutos e segundos."""
    image = Image.new("RGB", (64, 48), (10, 20, 30))
    exif = image.getexif()

    gps = exif.get_ifd(ExifTags.IFD.GPSInfo)
    gps[ExifTags.GPS.GPSLatitude.value] = tuple(IFDRational(part) for part in latitude)
    gps[ExifTags.GPS.GPSLatitudeRef.value] = latitude_ref
    gps[ExifTags.GPS.GPSLongitude.value] = tuple(IFDRational(part) for part in longitude)
    gps[ExifTags.GPS.GPSLongitudeRef.value] = longitude_ref

    image.save(path, format="JPEG", exif=exif)
    return path


def write_decompression_bomb(path: Path, width: int, height: int) -> Path:
    """Monta um PNG minusculo que DECLARA dimensoes gigantescas.

    O arquivo tem poucos bytes, mas o cabecalho IHDR anuncia uma imagem
    enorme. E exatamente a forma do ataque: quem decodificar isso tenta alocar
    width * height * 4 bytes de memoria.

    Construido a mao porque nenhuma biblioteca gera de boa vontade um arquivo
    cujo cabecalho mente sobre o conteudo.
    """

    def chunk(kind: bytes, data: bytes) -> bytes:
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)

    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(b"\x00" * 16))
        + chunk(b"IEND", b"")
    )
    return path


class TestBasicProperties:
    """Dimensoes, formato e modo de cor."""

    def test_reads_dimensions(self, tmp_path: Path) -> None:
        result = analyze_image(write_image(tmp_path / "foto.jpg", size=(640, 480)))

        assert result.width == 640
        assert result.height == 480

    def test_reads_format_and_color_mode(self, tmp_path: Path) -> None:
        result = analyze_image(write_image(tmp_path / "foto.jpg"))

        assert result.image_format == "JPEG"
        assert result.color_mode == "RGB"

    def test_calculates_megapixels(self, tmp_path: Path) -> None:
        result = analyze_image(write_image(tmp_path / "foto.jpg", size=(2000, 1500)))

        assert result.megapixels == 3.0

    def test_megapixels_is_none_without_dimensions(self, tmp_path: Path) -> None:
        corrupted = tmp_path / "quebrada.jpg"
        corrupted.write_bytes(b"\xff\xd8\xff" + b"\x00" * 32)

        assert analyze_image(corrupted).megapixels is None

    def test_reads_png_as_well(self, tmp_path: Path) -> None:
        result = analyze_image(write_image(tmp_path / "grafico.png", image_format="PNG"))

        assert result.image_format == "PNG"
        assert result.error is None


class TestExifExtraction:
    """Leitura dos metadados gravados pela camera ou pelo editor."""

    def test_reads_device_make_and_model(self, tmp_path: Path) -> None:
        path = write_image(tmp_path / "foto.jpg", Make="Apple", Model="iPhone 15 Pro")

        result = analyze_image(path)

        assert result.device_make == "Apple"
        assert result.device_model == "iPhone 15 Pro"

    def test_reads_editing_software(self, tmp_path: Path) -> None:
        """Software de edicao e informacao, nao acusacao.

        A maior parte das imagens profissionais passa por um editor.
        """
        path = write_image(tmp_path / "foto.jpg", Software="Adobe Photoshop 25.1")

        assert analyze_image(path).software == "Adobe Photoshop 25.1"

    def test_reads_the_timestamp(self, tmp_path: Path) -> None:
        path = write_image(tmp_path / "foto.jpg", DateTime="2026:10:15 09:12:00")

        assert analyze_image(path).created_at == "2026:10:15 09:12:00"

    def test_exposes_every_readable_tag(self, tmp_path: Path) -> None:
        path = write_image(tmp_path / "foto.jpg", Make="Canon", Model="EOS R5")

        exif = analyze_image(path).exif

        assert exif["Make"] == "Canon"
        assert exif["Model"] == "EOS R5"

    def test_image_without_exif_is_not_an_error(self, tmp_path: Path) -> None:
        """O caso mais comum do mundo real.

        Toda rede social remove o EXIF ao publicar. Uma foto sem metadado
        provavelmente so passou por um aplicativo de mensagem - e isso nunca
        e suspeito.
        """
        result = analyze_image(write_image(tmp_path / "limpa.jpg"))

        assert result.exif == {}
        assert result.error is None
        assert result.width == 64


class TestGpsExtraction:
    """Conversao de coordenadas para graus decimais."""

    def test_converts_south_west_coordinates(self, tmp_path: Path) -> None:
        """22 graus 7 minutos 12 segundos Sul = -22.12.

        O calculo e graus + minutos/60 + segundos/3600, com sinal negativo
        para Sul e Oeste. Estes sao os valores do exemplo da especificacao.
        """
        path = write_image_with_gps(
            tmp_path / "foto.jpg",
            latitude=(22, 7, 12),
            latitude_ref="S",
            longitude=(51, 23, 24),
            longitude_ref="W",
        )

        gps = analyze_image(path).gps

        assert gps is not None
        assert gps.latitude == pytest.approx(-22.12)
        assert gps.longitude == pytest.approx(-51.39)

    def test_converts_north_east_coordinates(self, tmp_path: Path) -> None:
        """Norte e Leste ficam positivos."""
        path = write_image_with_gps(
            tmp_path / "foto.jpg",
            latitude=(48, 51, 30),
            latitude_ref="N",
            longitude=(2, 17, 40),
            longitude_ref="E",
        )

        gps = analyze_image(path).gps

        assert gps is not None
        assert gps.latitude > 0
        assert gps.longitude > 0

    def test_image_without_gps_returns_none(self, tmp_path: Path) -> None:
        assert analyze_image(write_image(tmp_path / "foto.jpg")).gps is None


class TestDecompressionBomb:
    """Protecao contra imagem que declara dimensoes impossiveis."""

    def test_detects_a_bomb(self, tmp_path: Path) -> None:
        """Arquivo minusculo declarando dimensoes gigantescas.

        O teste prova que a leitura e segura: o arquivo tem poucos bytes, o
        cabecalho anuncia bilhoes de pixels, e a analise termina normalmente
        em vez de consumir toda a memoria.
        """
        path = write_decompression_bomb(tmp_path / "bomba.png", 60_000, 60_000)

        result = analyze_image(path)

        assert result.decompression_bomb is True

    def test_the_file_is_tiny_despite_the_declared_size(self, tmp_path: Path) -> None:
        """Deixa explicito o desproposito entre tamanho e dimensoes."""
        path = write_decompression_bomb(tmp_path / "bomba.png", 60_000, 60_000)

        assert path.stat().st_size < 1024
        assert 60_000 * 60_000 > MAX_SAFE_PIXELS

    def test_an_ordinary_image_is_not_a_bomb(self, tmp_path: Path) -> None:
        result = analyze_image(write_image(tmp_path / "foto.jpg", size=(4032, 3024)))

        assert result.decompression_bomb is False


class TestHostileInput:
    """Arquivos malformados nao podem derrubar a analise."""

    def test_a_non_image_returns_an_error_instead_of_raising(self, tmp_path: Path) -> None:
        not_an_image = tmp_path / "documento.pdf"
        not_an_image.write_bytes(b"%PDF-1.7\n" + b"\x00" * 64)

        result = analyze_image(not_an_image)

        assert result.error is not None
        assert result.width is None

    def test_a_truncated_image_returns_an_error(self, tmp_path: Path) -> None:
        truncated = tmp_path / "cortada.jpg"
        truncated.write_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF")

        assert analyze_image(truncated).error is not None

    def test_an_empty_file_returns_an_error(self, tmp_path: Path) -> None:
        empty = tmp_path / "vazia.jpg"
        empty.write_bytes(b"")

        assert analyze_image(empty).error is not None

    def test_a_missing_file_returns_an_error(self, tmp_path: Path) -> None:
        """Nem um caminho inexistente pode levantar excecao."""
        assert analyze_image(tmp_path / "nao-existe.jpg").error is not None
