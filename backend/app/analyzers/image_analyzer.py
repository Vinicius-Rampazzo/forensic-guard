"""Analise forense de imagens: dimensoes, EXIF e GPS.

O que EXIF carrega
------------------
Camera e celular gravam dentro da propria foto um bloco de metadados: marca e
modelo do aparelho, data e hora, software usado para editar, orientacao,
parametros de exposicao e, quando o GPS esta ligado, as coordenadas exatas de
onde a foto foi tirada.

Em perícia isso responde perguntas que a imagem sozinha nao responde: com que
aparelho foi feita, quando, e se passou por algum editor.

Duas leituras que NAO devem ser feitas
--------------------------------------
1. **Ausencia de EXIF nao e suspeita.** Toda rede social remove esses dados ao
   publicar, justamente por privacidade. Uma foto sem EXIF provavelmente so
   passou pelo WhatsApp.
2. **GPS nao e indicador de malicia.** E questao de privacidade: a pessoa
   normalmente nao sabe que compartilhou a localizacao de casa junto com a
   foto. Por isso o indicador correspondente vale zero ponto - ele informa,
   nao acusa.

Seguranca ao abrir imagem nao confiavel
---------------------------------------
`Image.open()` do Pillow e **preguicoso**: ele le apenas o cabecalho e nao
decodifica nenhum pixel. A decodificacao so acontece em `.load()`, `.convert()`
ou ao salvar - e este modulo nunca chama nada disso.

Isso importa porque existe um ataque chamado **decompression bomb**: um arquivo
de poucos quilobytes que declara ter dezenas de milhares de pixels de lado. Ao
ser decodificado, ele exige gigabytes de memoria e derruba o servico. Lendo so
o cabecalho, a bomba nunca detona - e ainda da para reportar a tentativa.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from PIL import ExifTags, Image

# Limite de pixels acima do qual a imagem e tratada como tentativa de bomba.
#
# 250 milhoes de pixels equivalem a mais de 15.000 x 15.000 - acima de qualquer
# camera real, inclusive dos celulares de 200 MP. Bombas de verdade declaram
# bilhoes de pixels.
#
# O valor tambem e aplicado ao Pillow, na importacao do modulo, para que ele
# recuse decodificar algo desse tamanho caso alguem venha a chamar .load() no
# futuro. A atribuicao acontece uma unica vez, e nao por requisicao: alterar
# configuracao global a cada chamada nao seria seguro com varias threads.
MAX_SAFE_PIXELS = 250_000_000

Image.MAX_IMAGE_PIXELS = MAX_SAFE_PIXELS

# Limites de extracao de EXIF. O bloco vem de arquivo nao confiavel e pode ter
# sido montado para ocupar memoria: milhares de tags, ou uma tag com megabytes
# de texto.
MAX_EXIF_TAGS = 120
MAX_EXIF_VALUE_LENGTH = 256


@dataclass(frozen=True)
class GpsCoordinates:
    """Coordenadas em graus decimais, prontas para um mapa."""

    latitude: float
    longitude: float


@dataclass(frozen=True)
class ImageAnalysis:
    """O que se conseguiu observar sobre a imagem.

    Attributes:
        width: largura em pixels, quando legivel.
        height: altura em pixels, quando legivel.
        image_format: formato reconhecido pelo Pillow (JPEG, PNG, ...).
        color_mode: modo de cor (RGB, RGBA, L, CMYK, ...).
        exif: todas as tags EXIF legiveis, ja convertidas para texto.
        device_make: fabricante do aparelho.
        device_model: modelo do aparelho.
        software: programa que gravou ou editou a imagem.
        created_at: data e hora registradas na imagem.
        gps: coordenadas, quando presentes.
        decompression_bomb: True quando a imagem declara mais pixels que o
            limite seguro.
        error: motivo pelo qual a leitura falhou, quando falhou. Ter o campo
            evita que um arquivo corrompido derrube a analise inteira.
    """

    width: int | None = None
    height: int | None = None
    image_format: str | None = None
    color_mode: str | None = None
    exif: dict[str, str] = field(default_factory=dict)
    device_make: str | None = None
    device_model: str | None = None
    software: str | None = None
    created_at: str | None = None
    gps: GpsCoordinates | None = None
    decompression_bomb: bool = False
    error: str | None = None

    @property
    def megapixels(self) -> float | None:
        """Total de pixels em milhoes, arredondado."""
        if self.width is None or self.height is None:
            return None

        return round(self.width * self.height / 1_000_000, 2)


def analyze_image(path: Path) -> ImageAnalysis:
    """Extrai dimensoes, metadados EXIF e GPS de uma imagem.

    Nunca decodifica os pixels. Qualquer falha de leitura vira o campo `error`,
    nunca excecao: a imagem vem de origem nao confiavel, e um arquivo
    corrompido ou deliberadamente malformado nao pode interromper a analise das
    outras partes da evidencia.
    """
    try:
        with warnings.catch_warnings():
            # O Pillow avisa com um WARNING quando a imagem passa do limite de
            # pixels, e so levanta excecao ao dobro disso. Transformar o aviso
            # em erro aqui garante que os dois casos recebam o mesmo
            # tratamento, em vez de o primeiro passar despercebido.
            warnings.simplefilter("error", Image.DecompressionBombWarning)

            with Image.open(path) as image:
                return _analyze_open_image(image)

    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        # A imagem declara mais pixels do que seria seguro decodificar. Como a
        # leitura parou no cabecalho, as dimensoes nao chegaram a ser lidas.
        return ImageAnalysis(
            decompression_bomb=True,
            error="Image declares more pixels than the safe limit",
        )
    except Image.UnidentifiedImageError:
        return ImageAnalysis(error="Not a readable image")
    except Exception as error:  # noqa: BLE001 - parser sobre entrada hostil
        # Captura ampla de proposito. Os decodificadores do Pillow lidam com
        # dezenas de formatos e levantam excecoes variadas diante de arquivos
        # malformados. Nenhuma delas pode derrubar a analise.
        return ImageAnalysis(error=f"Could not read image: {type(error).__name__}")


def _analyze_open_image(image: Image.Image) -> ImageAnalysis:
    """Le os metadados de uma imagem ja aberta, sem decodificar pixels."""
    width, height = image.size
    raw_exif = image.getexif()

    exif = _readable_tags(raw_exif)
    exif.update(_readable_tags(raw_exif.get_ifd(ExifTags.IFD.Exif)))

    return ImageAnalysis(
        width=width,
        height=height,
        image_format=image.format,
        color_mode=image.mode,
        exif=exif,
        device_make=exif.get("Make"),
        device_model=exif.get("Model"),
        software=exif.get("Software"),
        created_at=exif.get("DateTimeOriginal") or exif.get("DateTime"),
        gps=_extract_gps(raw_exif),
        decompression_bomb=width * height > MAX_SAFE_PIXELS,
    )


def _readable_tags(raw: Any) -> dict[str, str]:
    """Converte um bloco de tags EXIF em texto legivel.

    Os valores brutos vem em tipos variados - bytes, fracoes, tuplas - e
    precisam virar texto para caber no JSON da resposta. Tags sem nome
    conhecido sao descartadas: um numero solto nao diz nada a quem le o
    relatorio.
    """
    tags: dict[str, str] = {}

    for tag_id, value in list(raw.items())[:MAX_EXIF_TAGS]:
        name = ExifTags.TAGS.get(tag_id)

        if name is None:
            continue

        text = _readable_value(value)

        if text:
            tags[name] = text

    return tags


def _readable_value(value: Any) -> str:
    """Converte um valor EXIF em texto curto e seguro.

    Trunca valores longos: uma tag pode ter sido preenchida com megabytes de
    texto justamente para inchar a resposta.
    """
    if isinstance(value, bytes):
        # errors="replace" porque bytes arbitrarios nao formam texto valido, e
        # descartar a tag inteira perderia informacao util.
        value = value.decode("utf-8", errors="replace")

    text = str(value).strip().replace("\x00", "")

    return text[:MAX_EXIF_VALUE_LENGTH]


def _extract_gps(raw_exif: Any) -> GpsCoordinates | None:
    """Converte as coordenadas EXIF para graus decimais.

    O EXIF grava latitude e longitude em graus, minutos e segundos, com o
    hemisferio num campo separado:

        GPSLatitude    = (22, 7, 12)
        GPSLatitudeRef = "S"

    A conversao e direta - graus + minutos/60 + segundos/3600 - e o hemisferio
    define o sinal: Sul e Oeste sao negativos. O exemplo acima vira -22.12.
    """
    try:
        gps_data = raw_exif.get_ifd(ExifTags.IFD.GPSInfo)
    except Exception:  # noqa: BLE001 - bloco GPS malformado nao e erro fatal
        return None

    if not gps_data:
        return None

    latitude = _to_decimal_degrees(
        gps_data.get(ExifTags.GPS.GPSLatitude),
        gps_data.get(ExifTags.GPS.GPSLatitudeRef),
        negative_reference="S",
    )
    longitude = _to_decimal_degrees(
        gps_data.get(ExifTags.GPS.GPSLongitude),
        gps_data.get(ExifTags.GPS.GPSLongitudeRef),
        negative_reference="W",
    )

    if latitude is None or longitude is None:
        return None

    return GpsCoordinates(latitude=latitude, longitude=longitude)


def _to_decimal_degrees(
    dms: Any,
    reference: Any,
    negative_reference: str,
) -> float | None:
    """Converte graus/minutos/segundos em graus decimais.

    Devolve None diante de qualquer dado inesperado. Coordenada vinda de
    arquivo nao confiavel pode estar incompleta, com divisao por zero nas
    fracoes ou com tipos estranhos - e nada disso justifica interromper a
    analise.
    """
    if not dms or len(dms) != 3:
        return None

    try:
        degrees, minutes, seconds = (float(part) for part in dms)
    except (TypeError, ValueError, ZeroDivisionError):
        return None

    value = degrees + minutes / 60 + seconds / 3600

    if isinstance(reference, str) and reference.strip().upper() == negative_reference:
        value = -value

    # Fora da faixa valida o dado nao serve - e marcar um ponto errado no mapa
    # e pior que nao marcar nenhum.
    if not -180.0 <= value <= 180.0:
        return None

    return round(value, 6)
