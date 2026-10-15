"""Tabela de assinaturas de arquivo (magic bytes).

O conceito
----------
A extensao de um arquivo e apenas um pedaco do nome: qualquer pessoa renomeia
`payload.exe` para `foto.jpg` em dois segundos. Ja os primeiros bytes sao
escritos pelo programa que criou o arquivo e precisam estar la para que ele
funcione.

    extensao = o que o arquivo DIZ que e    (afirmacao, pode ser mentira)
    magic bytes = o que o arquivo E         (fato, verificavel)

Comparar os dois e o que produz o indicador mais forte do ForensicGuard: o
executavel disfarcado.

Este modulo e DADO, nao logica
------------------------------
As classes abaixo sao apenas recipientes - nenhuma delas tem metodo. Toda a
logica de comparacao vive em `app/utils/signatures.py`.

A separacao existe para que adicionar um formato novo seja uma entrada nesta
lista, sem tocar em codigo algum. E tambem porque, como regra do projeto,
`constants/` guarda dados e `utils/` guarda comportamento.

Por que uma LISTA de padroes por formato
----------------------------------------
Nem todo formato se identifica pelos primeiros bytes. WEBP, WAV e AVI sao
todos contaminers RIFF: os quatro primeiros bytes de todos eles sao `RIFF`, e o
que os diferencia esta no byte 8.

    RIFF....WEBP   ->  imagem WebP
    RIFF....WAVE   ->  audio WAV
    RIFF....AVI    ->  video AVI

Um modelo de "um prefixo por formato" classificaria os tres como a mesma coisa.
Por isso cada formato carrega varios padroes, e so casa quando TODOS casam.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class FileCategory(StrEnum):
    """Familia a que um formato pertence.

    Serve a duas coisas: escolher qual analisador especifico executar (imagem
    passa pelo analisador de EXIF) e calibrar a gravidade de um mismatch - um
    executavel disfarcado de documento e muito mais grave que um `.png`
    nomeado como `.jpg`.
    """

    IMAGE = "image"
    DOCUMENT = "document"
    ARCHIVE = "archive"
    EXECUTABLE = "executable"
    MEDIA = "media"
    EMAIL = "email"
    DATABASE = "database"
    OTHER = "other"


@dataclass(frozen=True)
class BytePattern:
    """Uma sequencia de bytes que deve aparecer numa posicao especifica.

    Attributes:
        magic: os bytes esperados.
        offset: a partir de qual byte do arquivo eles devem aparecer.
            Zero na maioria dos formatos, mas nao em todos: contaminers RIFF
            carregam o subtipo no byte 8, e a familia MP4/HEIC comeca com o
            tamanho do bloco antes do marcador `ftyp`.
    """

    magic: bytes
    offset: int = 0


@dataclass(frozen=True)
class FileSignature:
    """Descricao de um formato de arquivo reconhecivel.

    Attributes:
        name: nome legivel, exibido no relatorio.
        mime: tipo MIME correspondente.
        category: familia do formato.
        extensions: extensoes legitimas para este formato. Usar `.jpeg` num
            JPEG nao e mismatch - por isso a lista, e nao uma extensao so.
        patterns: todos precisam casar para o formato ser reconhecido.
        container_extensions: extensoes de formatos que USAM este como
            involucro. Um `.docx` e um ZIP por dentro: detectar "ZIP" num
            arquivo `.docx` esta correto e NAO deve virar indicador.
        note: observacao exibida no relatorio quando relevante.
    """

    name: str
    mime: str
    category: FileCategory
    extensions: tuple[str, ...]
    patterns: tuple[BytePattern, ...]
    container_extensions: tuple[str, ...] = ()
    note: str = ""


# ---------------------------------------------------------------------------
# Imagens
# ---------------------------------------------------------------------------

IMAGE_SIGNATURES = (
    FileSignature(
        name="JPEG image",
        mime="image/jpeg",
        category=FileCategory.IMAGE,
        extensions=(".jpg", ".jpeg", ".jpe", ".jfif"),
        patterns=(BytePattern(b"\xff\xd8\xff"),),
    ),
    FileSignature(
        name="PNG image",
        mime="image/png",
        category=FileCategory.IMAGE,
        extensions=(".png",),
        # Os bytes \r\n\x1a\n existem de proposito: detectam corrupcao causada
        # por transferencia em modo texto, que converteria essas quebras.
        patterns=(BytePattern(b"\x89PNG\r\n\x1a\n"),),
    ),
    FileSignature(
        name="GIF image (87a)",
        mime="image/gif",
        category=FileCategory.IMAGE,
        extensions=(".gif",),
        patterns=(BytePattern(b"GIF87a"),),
    ),
    FileSignature(
        name="GIF image (89a)",
        mime="image/gif",
        category=FileCategory.IMAGE,
        extensions=(".gif",),
        patterns=(BytePattern(b"GIF89a"),),
    ),
    FileSignature(
        name="BMP image",
        mime="image/bmp",
        category=FileCategory.IMAGE,
        extensions=(".bmp", ".dib"),
        # Apenas dois bytes: assinatura fraca, casa por acaso com facilidade.
        patterns=(BytePattern(b"BM"),),
    ),
    FileSignature(
        name="TIFF image (little-endian)",
        mime="image/tiff",
        category=FileCategory.IMAGE,
        extensions=(".tif", ".tiff"),
        patterns=(BytePattern(b"II*\x00"),),
    ),
    FileSignature(
        name="TIFF image (big-endian)",
        mime="image/tiff",
        category=FileCategory.IMAGE,
        extensions=(".tif", ".tiff"),
        patterns=(BytePattern(b"MM\x00*"),),
    ),
    FileSignature(
        name="WebP image",
        mime="image/webp",
        category=FileCategory.IMAGE,
        extensions=(".webp",),
        # Container RIFF: o subtipo esta no byte 8. Sem o segundo padrao,
        # arquivos WAV e AVI seriam classificados como WebP.
        patterns=(BytePattern(b"RIFF"), BytePattern(b"WEBP", offset=8)),
    ),
    FileSignature(
        name="Windows icon",
        mime="image/x-icon",
        category=FileCategory.IMAGE,
        extensions=(".ico",),
        patterns=(BytePattern(b"\x00\x00\x01\x00"),),
    ),
    FileSignature(
        name="HEIF/HEIC image",
        mime="image/heic",
        category=FileCategory.IMAGE,
        extensions=(".heic", ".heif"),
        # Familia ISO-BMFF: os 4 primeiros bytes sao o tamanho do bloco, entao
        # o marcador comeca no byte 4 e a marca do formato no byte 8.
        patterns=(BytePattern(b"ftyp", offset=4), BytePattern(b"heic", offset=8)),
    ),
)


# ---------------------------------------------------------------------------
# Documentos
# ---------------------------------------------------------------------------

DOCUMENT_SIGNATURES = (
    FileSignature(
        name="PDF document",
        mime="application/pdf",
        category=FileCategory.DOCUMENT,
        extensions=(".pdf",),
        patterns=(BytePattern(b"%PDF-"),),
    ),
    FileSignature(
        name="Rich Text Format",
        mime="application/rtf",
        category=FileCategory.DOCUMENT,
        extensions=(".rtf",),
        patterns=(BytePattern(b"{\\rtf1"),),
    ),
    FileSignature(
        name="Microsoft Office (OLE2 compound file)",
        mime="application/x-ole-storage",
        category=FileCategory.DOCUMENT,
        extensions=(".doc", ".xls", ".ppt", ".msg", ".vsd"),
        patterns=(BytePattern(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"),),
        note=(
            "Legacy Office container. This format can carry VBA macros; "
            "ForensicGuard does not execute or parse them."
        ),
    ),
)


# ---------------------------------------------------------------------------
# Arquivos compactados
# ---------------------------------------------------------------------------

ARCHIVE_SIGNATURES = (
    FileSignature(
        name="ZIP archive",
        mime="application/zip",
        category=FileCategory.ARCHIVE,
        extensions=(".zip",),
        patterns=(BytePattern(b"PK\x03\x04"),),
        # Todos esses formatos sao ZIP por dentro. Detectar "ZIP" num .docx
        # esta CORRETO e nao deve gerar indicador de mismatch.
        container_extensions=(
            ".docx",
            ".xlsx",
            ".pptx",
            ".odt",
            ".ods",
            ".odp",
            ".jar",
            ".apk",
            ".epub",
            ".vsdx",
        ),
        note=(
            "Modern Office and OpenDocument files are ZIP containers. "
            "Inspecting the archive contents is out of scope for now."
        ),
    ),
    FileSignature(
        name="ZIP archive (empty)",
        mime="application/zip",
        category=FileCategory.ARCHIVE,
        extensions=(".zip",),
        patterns=(BytePattern(b"PK\x05\x06"),),
    ),
    FileSignature(
        name="RAR archive (v1.5-4.x)",
        mime="application/vnd.rar",
        category=FileCategory.ARCHIVE,
        extensions=(".rar",),
        patterns=(BytePattern(b"Rar!\x1a\x07\x00"),),
    ),
    FileSignature(
        name="RAR archive (v5+)",
        mime="application/vnd.rar",
        category=FileCategory.ARCHIVE,
        extensions=(".rar",),
        patterns=(BytePattern(b"Rar!\x1a\x07\x01\x00"),),
    ),
    FileSignature(
        name="7-Zip archive",
        mime="application/x-7z-compressed",
        category=FileCategory.ARCHIVE,
        extensions=(".7z",),
        patterns=(BytePattern(b"7z\xbc\xaf\x27\x1c"),),
    ),
    FileSignature(
        name="GZIP archive",
        mime="application/gzip",
        category=FileCategory.ARCHIVE,
        extensions=(".gz", ".tgz"),
        patterns=(BytePattern(b"\x1f\x8b"),),
    ),
    FileSignature(
        name="BZIP2 archive",
        mime="application/x-bzip2",
        category=FileCategory.ARCHIVE,
        extensions=(".bz2",),
        patterns=(BytePattern(b"BZh"),),
    ),
    FileSignature(
        name="XZ archive",
        mime="application/x-xz",
        category=FileCategory.ARCHIVE,
        extensions=(".xz",),
        patterns=(BytePattern(b"\xfd7zXZ\x00"),),
    ),
)


# ---------------------------------------------------------------------------
# Executaveis
#
# Categoria mais sensivel da tabela: um executavel com extensao de documento ou
# de imagem e o indicador de maior peso do projeto.
# ---------------------------------------------------------------------------

EXECUTABLE_SIGNATURES = (
    FileSignature(
        name="Windows executable (PE / MZ)",
        mime="application/vnd.microsoft.portable-executable",
        category=FileCategory.EXECUTABLE,
        extensions=(".exe", ".dll", ".sys", ".scr", ".ocx", ".cpl", ".drv"),
        # Apenas dois bytes - a assinatura mais fraca da tabela. Em compensacao,
        # e a de maior consequencia quando a extensao nao combina.
        patterns=(BytePattern(b"MZ"),),
    ),
    FileSignature(
        name="Linux executable (ELF)",
        mime="application/x-executable",
        category=FileCategory.EXECUTABLE,
        extensions=(".so", ".elf", ".bin"),
        patterns=(BytePattern(b"\x7fELF"),),
    ),
    FileSignature(
        name="macOS executable (Mach-O 32-bit)",
        mime="application/x-mach-binary",
        category=FileCategory.EXECUTABLE,
        extensions=(),
        patterns=(BytePattern(b"\xce\xfa\xed\xfe"),),
    ),
    FileSignature(
        name="macOS executable (Mach-O 64-bit)",
        mime="application/x-mach-binary",
        category=FileCategory.EXECUTABLE,
        extensions=(),
        patterns=(BytePattern(b"\xcf\xfa\xed\xfe"),),
    ),
    FileSignature(
        name="Java class file",
        mime="application/java-vm",
        category=FileCategory.EXECUTABLE,
        extensions=(".class",),
        patterns=(BytePattern(b"\xca\xfe\xba\xbe"),),
        note=(
            "These bytes are also used by Mach-O universal binaries. "
            "Treat the detected type as ambiguous."
        ),
    ),
    FileSignature(
        name="Windows shortcut",
        mime="application/x-ms-shortcut",
        category=FileCategory.EXECUTABLE,
        extensions=(".lnk",),
        patterns=(BytePattern(b"\x4c\x00\x00\x00\x01\x14\x02\x00"),),
        note=(
            "Shortcuts can launch arbitrary commands and are a common "
            "phishing delivery format."
        ),
    ),
    FileSignature(
        name="Script with shebang",
        mime="text/x-script",
        category=FileCategory.EXECUTABLE,
        extensions=(".sh", ".py", ".pl", ".rb"),
        patterns=(BytePattern(b"#!"),),
    ),
)


# ---------------------------------------------------------------------------
# Midia
#
# Presentes sobretudo para evitar falso positivo: sem WAV e AVI aqui, qualquer
# container RIFF seria classificado como imagem WebP.
# ---------------------------------------------------------------------------

MEDIA_SIGNATURES = (
    FileSignature(
        name="WAV audio",
        mime="audio/wav",
        category=FileCategory.MEDIA,
        extensions=(".wav",),
        patterns=(BytePattern(b"RIFF"), BytePattern(b"WAVE", offset=8)),
    ),
    FileSignature(
        name="AVI video",
        mime="video/x-msvideo",
        category=FileCategory.MEDIA,
        extensions=(".avi",),
        patterns=(BytePattern(b"RIFF"), BytePattern(b"AVI ", offset=8)),
    ),
    FileSignature(
        name="MP3 audio (ID3)",
        mime="audio/mpeg",
        category=FileCategory.MEDIA,
        extensions=(".mp3",),
        patterns=(BytePattern(b"ID3"),),
    ),
    FileSignature(
        name="MP4 container",
        mime="video/mp4",
        category=FileCategory.MEDIA,
        extensions=(".mp4", ".m4a", ".m4v", ".mov"),
        patterns=(BytePattern(b"ftyp", offset=4),),
    ),
)


# ---------------------------------------------------------------------------
# Outros formatos de interesse forense
# ---------------------------------------------------------------------------

OTHER_SIGNATURES = (
    FileSignature(
        name="SQLite database",
        mime="application/vnd.sqlite3",
        category=FileCategory.DATABASE,
        extensions=(".sqlite", ".sqlite3", ".db"),
        patterns=(BytePattern(b"SQLite format 3\x00"),),
        note="Browser history, messaging apps and mobile backups use SQLite.",
    ),
)


# Tabela completa, na ordem em que as familias foram declaradas.
# A ordem nao decide o resultado: quando mais de um formato casa, vence o que
# confirmou mais bytes. Isso e resolvido em `app/utils/signatures.py`.
SIGNATURES: tuple[FileSignature, ...] = (
    *IMAGE_SIGNATURES,
    *DOCUMENT_SIGNATURES,
    *ARCHIVE_SIGNATURES,
    *EXECUTABLE_SIGNATURES,
    *MEDIA_SIGNATURES,
    *OTHER_SIGNATURES,
)


# Quantos bytes do inicio do arquivo bastam para avaliar todas as assinaturas.
#
# Calculado a partir da propria tabela, e nao escrito a mao: adicionar um
# formato com offset maior ajusta este valor sozinho. Numero magico escrito a
# mao aqui seria uma fonte silenciosa de erro no dia em que alguem esquecesse
# de atualiza-lo.
SIGNATURE_READ_SIZE = max(
    pattern.offset + len(pattern.magic)
    for signature in SIGNATURES
    for pattern in signature.patterns
)


# ---------------------------------------------------------------------------
# E-mail
#
# Arquivos .eml nao tem magic bytes: sao texto puro comecando direto nos
# cabecalhos. A deteccao e heuristica, baseada na presenca de cabecalhos
# obrigatorios definidos na RFC 5322.
# ---------------------------------------------------------------------------

# Cabecalhos procurados no inicio de linha. Em minusculas porque a comparacao
# ignora caixa - a RFC permite qualquer combinacao.
EMAIL_HEADERS = (
    "from:",
    "to:",
    "cc:",
    "bcc:",
    "subject:",
    "date:",
    "message-id:",
    "received:",
    "return-path:",
    "reply-to:",
    "mime-version:",
    "content-type:",
    "authentication-results:",
    "dkim-signature:",
    "x-mailer:",
)

# Quantos cabecalhos distintos bastam para classificar como e-mail.
#
# Tres e o equilibrio entre os dois erros possiveis: com um so, qualquer texto
# contendo "Date:" viraria e-mail; exigindo muitos, mensagens minimas ou
# truncadas escapariam. Um e-mail valido sempre carrega pelo menos From, Date e
# um identificador.
MINIMUM_EMAIL_HEADERS = 3

# Quantos bytes do inicio do arquivo sao lidos em busca dos cabecalhos.
# Cabecalhos de e-mail ficam sempre no comeco, antes do corpo.
EMAIL_HEADER_SCAN_SIZE = 8 * 1024
