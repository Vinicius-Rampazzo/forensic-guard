"""Testes da identificacao de evidencia e da regra de mismatch.

A regra de mismatch e o coracao desta etapa, e o risco dela nao e deixar de
achar contradicao - e gritar a toa. Boa parte dos testes abaixo verifica
justamente os casos em que NAO deve haver indicador.
"""

from pathlib import Path

from app.constants.signatures import FileCategory
from app.services.evidence_detector import (
    EvidenceType,
    MismatchKind,
    classify_mismatch,
    compare_opinions,
    detect_evidence,
    extract_extension,
)
from app.utils.signatures import detect_signature

PADDING = b"\x00" * 64

PNG = b"\x89PNG\r\n\x1a\n" + PADDING
JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF" + PADDING
PDF = b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n" + PADDING
ZIP = b"PK\x03\x04\x14\x00\x00\x00" + PADDING
WINDOWS_EXECUTABLE = b"MZ\x90\x00\x03\x00\x00\x00" + PADDING
PLAIN_TEXT = b"Relatorio trimestral de vendas.\nNada de especial aqui.\n" * 4

EMAIL = (
    b"Return-Path: <financeiro@empresa.com>\r\n"
    b"From: Financeiro <financeiro@empresa.com>\r\n"
    b"To: vitima@empresa.com\r\n"
    b"Subject: Fatura em atraso\r\n"
    b"Date: Mon, 15 Oct 2026 09:12:00 -0300\r\n"
    b"\r\n"
    b"Segue a fatura em anexo.\r\n"
)


def write(tmp_path: Path, name: str, data: bytes) -> Path:
    """Grava uma fixture em disco e devolve o caminho."""
    evidence = tmp_path / name
    evidence.write_bytes(data)
    return evidence


class TestExtensionExtraction:
    """Leitura da extensao a partir de um nome de arquivo nao confiavel."""

    def test_extracts_a_simple_extension(self) -> None:
        assert extract_extension("invoice.pdf") == ".pdf"

    def test_normalizes_to_lowercase(self) -> None:
        """`.JPG` e `.jpg` sao a mesma coisa; a tabela usa minusculas."""
        assert extract_extension("FOTO.JPG") == ".jpg"

    def test_uses_only_the_last_extension(self) -> None:
        """`relatorio.tar.gz` e um GZIP, nao um TAR."""
        assert extract_extension("relatorio.tar.gz") == ".gz"

    def test_returns_empty_when_there_is_no_extension(self) -> None:
        assert extract_extension("Makefile") == ""

    def test_handles_windows_path_separators(self) -> None:
        """Nome com separador de caminho nao confunde a extracao.

        O nome vem do usuario e pode trazer `..\\` numa tentativa de path
        traversal. Aqui ele nunca abre nada - so se le a extensao - mas a
        leitura precisa estar certa mesmo assim.
        """
        assert extract_extension(r"..\..\Windows\System32\evil.exe") == ".exe"

    def test_handles_posix_path_separators(self) -> None:
        assert extract_extension("../../etc/passwd.txt") == ".txt"

    def test_hidden_file_without_extension(self) -> None:
        """`.gitignore` e um nome, nao uma extensao."""
        assert extract_extension(".gitignore") == ""


class TestMismatchDetection:
    """Comparacao entre a extensao declarada e a assinatura real."""

    def test_matching_extension_is_not_a_mismatch(self) -> None:
        assert classify_mismatch(".png", detect_signature(PNG)) is MismatchKind.NONE

    def test_alternative_extension_is_not_a_mismatch(self) -> None:
        """`.jpeg` e `.jpg` sao o mesmo formato.

        Sem a lista de extensoes legitimas, metade das fotos do mundo viraria
        indicador.
        """
        assert classify_mismatch(".jpeg", detect_signature(JPEG)) is MismatchKind.NONE
        assert classify_mismatch(".jpg", detect_signature(JPEG)) is MismatchKind.NONE

    def test_container_extension_is_not_a_mismatch(self) -> None:
        """Um `.docx` E um ZIP por dentro - detectar ZIP ali esta correto."""
        for extension in (".docx", ".xlsx", ".pptx", ".jar", ".apk"):
            assert classify_mismatch(extension, detect_signature(ZIP)) is MismatchKind.NONE

    def test_unknown_format_cannot_produce_a_mismatch(self) -> None:
        """Sem assinatura reconhecida nao ha base para afirmar contradicao."""
        assert classify_mismatch(".txt", detect_signature(PLAIN_TEXT)) is MismatchKind.NONE

    def test_missing_extension_is_not_a_mismatch(self) -> None:
        """Sem extensao nao ha afirmacao a ser contradita."""
        assert classify_mismatch("", detect_signature(WINDOWS_EXECUTABLE)) is MismatchKind.NONE

    def test_executable_disguised_as_an_image(self) -> None:
        """O indicador mais importante do projeto.

        `invoice.jpg` cujos bytes comecam com `MZ`: o usuario acredita abrir
        uma fatura e executa um programa.
        """
        result = classify_mismatch(".jpg", detect_signature(WINDOWS_EXECUTABLE))

        assert result is MismatchKind.EXECUTABLE_DISGUISED

    def test_executable_disguised_as_a_document(self) -> None:
        result = classify_mismatch(".pdf", detect_signature(WINDOWS_EXECUTABLE))

        assert result is MismatchKind.EXECUTABLE_DISGUISED

    def test_executable_with_an_executable_extension_is_not_disguised(self) -> None:
        """Um `.exe` que e mesmo um executavel nao tem nada de errado."""
        for extension in (".exe", ".dll", ".sys"):
            result = classify_mismatch(extension, detect_signature(WINDOWS_EXECUTABLE))

            assert result is MismatchKind.NONE

    def test_plain_type_mismatch_is_separated_from_the_executable_case(self) -> None:
        """Nome errado e grave; executavel disfarcado e outro patamar.

        Separar os dois permite ao Risk Engine pontuar cada um conforme o que
        realmente representa.
        """
        result = classify_mismatch(".pdf", detect_signature(PNG))

        assert result is MismatchKind.TYPE_MISMATCH


class TestOpinionComparison:
    """Confronto entre a tabela propria e a biblioteca externa."""

    def test_agreement(self) -> None:
        assert compare_opinions("image/png", "image/png") is True

    def test_disagreement(self) -> None:
        assert compare_opinions("image/png", "application/zip") is False

    def test_missing_opinion_is_not_disagreement(self) -> None:
        """Ausencia de opiniao nao e discordancia - por isso None."""
        assert compare_opinions(None, "image/png") is None
        assert compare_opinions("image/png", None) is None
        assert compare_opinions(None, None) is None


class TestEvidenceTypeClassification:
    """Escolha do analisador que a evidencia percorrera adiante."""

    def test_image_is_routed_to_the_image_pipeline(self, tmp_path: Path) -> None:
        result = detect_evidence(write(tmp_path, "foto.png", PNG))

        assert result.evidence_type is EvidenceType.IMAGE

    def test_email_is_recognized_without_magic_bytes(self, tmp_path: Path) -> None:
        result = detect_evidence(write(tmp_path, "mensagem.eml", EMAIL))

        assert result.evidence_type is EvidenceType.EMAIL

    def test_email_is_recognized_despite_a_misleading_extension(self, tmp_path: Path) -> None:
        """Um phishing salvo como `.txt` continua sendo um e-mail.

        A classificacao olha o conteudo, nunca o nome - que e exatamente o
        principio desta etapa.
        """
        result = detect_evidence(write(tmp_path, "fatura.txt", EMAIL))

        assert result.evidence_type is EvidenceType.EMAIL

    def test_anything_else_is_a_generic_file(self, tmp_path: Path) -> None:
        result = detect_evidence(write(tmp_path, "documento.pdf", PDF))

        assert result.evidence_type is EvidenceType.FILE


class TestFullDetection:
    """Analise completa, do arquivo em disco ao resultado."""

    def test_identifies_a_legitimate_png(self, tmp_path: Path) -> None:
        result = detect_evidence(write(tmp_path, "grafico.png", PNG))

        assert result.detected_name == "PNG image"
        assert result.detected_mime == "image/png"
        assert result.detected_category is FileCategory.IMAGE
        assert result.declared_extension == ".png"
        assert result.mismatch is MismatchKind.NONE
        assert result.confirmed_bytes == 8
        assert result.second_opinion_agrees is True

    def test_identifies_an_executable_disguised_as_an_image(self, tmp_path: Path) -> None:
        """O cenario que motiva a etapa inteira."""
        result = detect_evidence(write(tmp_path, "invoice.jpg", WINDOWS_EXECUTABLE))

        assert result.mismatch is MismatchKind.EXECUTABLE_DISGUISED
        assert result.declared_extension == ".jpg"
        assert result.detected_category is FileCategory.EXECUTABLE
        assert result.detected_name == "Windows executable (PE / MZ)"

    def test_audits_the_original_filename_not_the_temporary_one(self, tmp_path: Path) -> None:
        """A extensao auditada vem do nome do upload, nao do arquivo em disco.

        Nas proximas etapas a evidencia sera gravada com um nome interno
        gerado por UUID, sem extensao alguma. Se a auditoria olhasse o caminho
        em disco, nenhum mismatch seria encontrado - o indicador principal do
        projeto deixaria de funcionar em producao.
        """
        on_disk = write(tmp_path, "a3f1c9d2-7b4e-4a11-9f03-2d8e5c6b7a90", WINDOWS_EXECUTABLE)

        result = detect_evidence(on_disk, original_filename="invoice.jpg")

        assert result.declared_extension == ".jpg"
        assert result.mismatch is MismatchKind.EXECUTABLE_DISGUISED

    def test_unknown_content_is_reported_honestly(self, tmp_path: Path) -> None:
        """Sem assinatura, o resultado diz que nao sabe - e nao chuta."""
        result = detect_evidence(write(tmp_path, "notas.txt", PLAIN_TEXT))

        assert result.detected_name is None
        assert result.detected_mime is None
        assert result.detected_category is None
        assert result.confirmed_bytes == 0
        assert result.mismatch is MismatchKind.NONE

    def test_empty_file_is_handled(self, tmp_path: Path) -> None:
        result = detect_evidence(write(tmp_path, "vazio.bin", b""))

        assert result.detected_name is None
        assert result.evidence_type is EvidenceType.FILE
        assert result.mismatch is MismatchKind.NONE

    def test_office_document_reports_its_container_nature(self, tmp_path: Path) -> None:
        """Um `.docx` e reportado como ZIP, com a observacao explicando."""
        result = detect_evidence(write(tmp_path, "contrato.docx", ZIP))

        assert result.detected_name == "ZIP archive"
        assert result.mismatch is MismatchKind.NONE
        assert any("ZIP containers" in note for note in result.notes)
