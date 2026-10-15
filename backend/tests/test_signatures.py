"""Testes do casamento de assinaturas.

Todas as fixtures sao construidas em codigo, byte a byte, a partir dos magic
bytes publicados de cada formato. Nenhum arquivo binario entra no repositorio.
"""

from pathlib import Path

from app.constants.signatures import SIGNATURE_READ_SIZE, SIGNATURES, BytePattern
from app.utils.signatures import (
    confirmed_bytes,
    count_email_headers,
    detect_signature,
    guess_with_puremagic,
    looks_like_email,
    match_signatures,
    pattern_matches,
    read_header,
    signature_matches,
)

# Cabecalhos minimos de cada formato, seguidos de enchimento para que o
# arquivo tenha tamanho realista.
PADDING = b"\x00" * 64

PNG = b"\x89PNG\r\n\x1a\n" + PADDING
JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF" + PADDING
PDF = b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n" + PADDING
ZIP = b"PK\x03\x04\x14\x00\x00\x00" + PADDING
WINDOWS_EXECUTABLE = b"MZ\x90\x00\x03\x00\x00\x00" + PADDING

# Containers RIFF: identicos nos 4 primeiros bytes, diferentes no byte 8.
WEBP = b"RIFF" + b"\x24\x00\x00\x00" + b"WEBP" + PADDING
WAV = b"RIFF" + b"\x24\x00\x00\x00" + b"WAVE" + PADDING
AVI = b"RIFF" + b"\x24\x00\x00\x00" + b"AVI " + PADDING

PLAIN_TEXT = b"Apenas um texto comum, sem assinatura nenhuma.\n" * 4

EMAIL = (
    b"Received: from mail.empresa.com (mail.empresa.com [203.0.113.10])\r\n"
    b"Return-Path: <financeiro@empresa.com>\r\n"
    b"From: Financeiro <financeiro@empresa.com>\r\n"
    b"To: vitima@empresa.com\r\n"
    b"Subject: Fatura em atraso\r\n"
    b"Date: Mon, 15 Oct 2026 09:12:00 -0300\r\n"
    b"Message-ID: <abc123@empresa.com>\r\n"
    b"\r\n"
    b"Segue a fatura em anexo.\r\n"
)


class TestPatternMatching:
    """Comparacao de um unico padrao de bytes."""

    def test_matches_at_offset_zero(self) -> None:
        assert pattern_matches(PNG, BytePattern(b"\x89PNG"))

    def test_matches_at_a_non_zero_offset(self) -> None:
        """Formatos como WebP carregam o marcador fora do inicio."""
        assert pattern_matches(WEBP, BytePattern(b"WEBP", offset=8))

    def test_does_not_match_the_wrong_offset(self) -> None:
        """Os bytes certos na posicao errada nao contam."""
        assert not pattern_matches(WEBP, BytePattern(b"WEBP", offset=0))

    def test_file_shorter_than_the_pattern_does_not_match(self) -> None:
        """Arquivo curto demais simplesmente nao casa - nao e erro.

        Um arquivo de 3 bytes nunca sera um WebP, que precisa de 12.
        """
        assert not pattern_matches(b"RIF", BytePattern(b"WEBP", offset=8))

    def test_empty_file_does_not_match_anything(self) -> None:
        assert not pattern_matches(b"", BytePattern(b"MZ"))


class TestSignatureMatching:
    """Um formato so e reconhecido quando TODOS os seus padroes casam."""

    def test_recognizes_a_single_pattern_format(self) -> None:
        png = next(signature for signature in SIGNATURES if signature.name == "PNG image")

        assert signature_matches(PNG, png)

    def test_riff_container_requires_the_subtype_marker(self) -> None:
        """O teste que justifica o modelo de multiplos padroes.

        WebP, WAV e AVI comecam identicos. Se o formato fosse reconhecido
        apenas pelos primeiros bytes, os tres seriam a mesma coisa.
        """
        webp = next(signature for signature in SIGNATURES if signature.name == "WebP image")

        assert signature_matches(WEBP, webp)
        assert not signature_matches(WAV, webp)
        assert not signature_matches(AVI, webp)

    def test_confirmed_bytes_sums_every_pattern(self) -> None:
        """A forca da evidencia soma todos os padroes conferidos."""
        webp = next(signature for signature in SIGNATURES if signature.name == "WebP image")

        # "RIFF" (4) + "WEBP" (4)
        assert confirmed_bytes(webp) == 8


class TestDetection:
    """Escolha do formato mais provavel entre os que casaram."""

    def test_detects_common_formats(self) -> None:
        for data, expected in [
            (PNG, "PNG image"),
            (JPEG, "JPEG image"),
            (PDF, "PDF document"),
            (ZIP, "ZIP archive"),
            (WINDOWS_EXECUTABLE, "Windows executable (PE / MZ)"),
            (WEBP, "WebP image"),
            (WAV, "WAV audio"),
            (AVI, "AVI video"),
        ]:
            match = detect_signature(data)

            assert match is not None, f"nao reconheceu {expected}"
            assert match.signature.name == expected

    def test_returns_none_for_content_without_signature(self) -> None:
        """Ausencia de assinatura e resultado legitimo, nao erro.

        Texto, CSV e JSON nao tem magic bytes - e isso nunca e suspeito.
        """
        assert detect_signature(PLAIN_TEXT) is None

    def test_returns_none_for_an_empty_file(self) -> None:
        assert detect_signature(b"") is None

    def test_stronger_evidence_wins(self) -> None:
        """Quando dois formatos casam, vence o que confirmou mais bytes.

        Estes bytes casam com WebP (8 bytes: RIFF + WEBP) e nao casam com mais
        nada. O teste protege a regra de ordenacao: se ela fosse por ordem de
        declaracao na tabela, um formato fraco declarado antes poderia vencer.
        """
        matches = match_signatures(WEBP)

        assert matches[0].signature.name == "WebP image"
        assert matches[0].confirmed_bytes == 8

    def test_matches_are_ordered_from_strongest_to_weakest(self) -> None:
        matches = match_signatures(WEBP)
        strengths = [match.confirmed_bytes for match in matches]

        assert strengths == sorted(strengths, reverse=True)


class TestSecondOpinion:
    """Consulta a biblioteca externa, usada como opiniao complementar."""

    def test_recognizes_a_known_format(self) -> None:
        assert guess_with_puremagic(PNG) == "image/png"

    def test_returns_none_instead_of_raising_for_unknown_content(self) -> None:
        """Conteudo nao reconhecido devolve None, nunca excecao.

        Esta funcao recebe bytes de origem hostil: um parser externo que
        levante excecao nao pode derrubar a analise inteira.
        """
        assert guess_with_puremagic(b"\x01\x02\x03nada aqui") is None

    def test_empty_input_is_handled(self) -> None:
        assert guess_with_puremagic(b"") is None


class TestEmailHeuristic:
    """Deteccao de e-mail por contagem de cabecalhos, sem magic bytes."""

    def test_recognizes_an_email(self) -> None:
        assert looks_like_email(EMAIL)

    def test_counts_distinct_headers_only(self) -> None:
        """Uma cadeia com varios Received: conta esse cabecalho uma vez so."""
        repeated = b"Received: a\r\nReceived: b\r\nReceived: c\r\n"

        assert count_email_headers(repeated) == 1
        assert not looks_like_email(repeated)

    def test_requires_the_header_at_the_start_of_a_line(self) -> None:
        """Mencionar cabecalhos no meio de um texto nao faz dele um e-mail.

        Sem essa regra, qualquer documento que explique e-mails - inclusive a
        documentacao deste projeto - seria classificado como mensagem.
        """
        prose = (
            b"O cabecalho From: identifica o remetente, "
            b"o Subject: traz o assunto e o Date: a data.\r\n"
        )

        assert not looks_like_email(prose)

    def test_plain_text_is_not_an_email(self) -> None:
        assert not looks_like_email(PLAIN_TEXT)

    def test_binary_content_does_not_break_the_decoding(self) -> None:
        """Bytes que nao formam texto valido sao descartados sem excecao."""
        assert not looks_like_email(WINDOWS_EXECUTABLE)

    def test_header_matching_ignores_case(self) -> None:
        """A RFC permite qualquer combinacao de maiusculas e minusculas."""
        shouting = b"FROM: a@b.com\r\nSUBJECT: teste\r\nDATE: hoje\r\n"

        assert looks_like_email(shouting)


class TestHeaderReading:
    """Leitura do inicio do arquivo."""

    def test_reads_only_the_beginning_of_a_large_file(self, tmp_path: Path) -> None:
        """Uma evidencia de gigabytes nao pode ser carregada inteira.

        Para reconhecer o formato bastam alguns milhares de bytes do comeco.
        """
        evidence = tmp_path / "large.bin"
        evidence.write_bytes(PNG + b"\x00" * (1024 * 1024))

        header = read_header(evidence)

        assert header.startswith(b"\x89PNG")
        assert len(header) < 1024 * 1024

    def test_reads_short_files_entirely(self, tmp_path: Path) -> None:
        evidence = tmp_path / "small.bin"
        evidence.write_bytes(b"MZ")

        assert read_header(evidence) == b"MZ"


class TestSignatureTableIntegrity:
    """Invariantes da propria tabela - protegem contra erro de digitacao."""

    def test_read_size_covers_every_pattern(self) -> None:
        """O tamanho de leitura e derivado da tabela, nao escrito a mao.

        Se alguem adicionar um formato com offset maior que o limite atual, o
        valor se ajusta sozinho. Este teste garante que a derivacao continua
        correta.
        """
        for signature in SIGNATURES:
            for pattern in signature.patterns:
                assert pattern.offset + len(pattern.magic) <= SIGNATURE_READ_SIZE

    def test_every_signature_has_at_least_one_pattern(self) -> None:
        """Uma assinatura sem padrao casaria com todo arquivo.

        O `all()` do casador devolve True para lista vazia - entao uma entrada
        incompleta na tabela classificaria qualquer coisa como aquele formato.
        """
        for signature in SIGNATURES:
            assert signature.patterns, f"{signature.name} nao tem padrao"

    def test_extensions_are_lowercase_and_start_with_a_dot(self) -> None:
        """A comparacao com a extensao declarada normaliza para minusculas."""
        for signature in SIGNATURES:
            for extension in signature.extensions + signature.container_extensions:
                assert extension.startswith("."), f"{signature.name}: {extension}"
                assert extension == extension.lower(), f"{signature.name}: {extension}"
