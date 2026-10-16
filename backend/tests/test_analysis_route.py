"""Testes da rota POST /analyze.

Testes de ponta a ponta: sobem um arquivo pelo cliente HTTP de teste e
verificam o JSON devolvido. Sao eles que provam que as pecas das Etapas 2 e 3
estao realmente costuradas.
"""

import io
import struct
import zlib
from email.message import EmailMessage
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import ExifTags, Image
from PIL.TiffImagePlugin import IFDRational

PADDING = b"\x00" * 64

PLAIN_TEXT = b"Relatorio trimestral. Nada de especial aqui.\n" * 4


def _build_png() -> bytes:
    """Gera um PNG valido de verdade, nao apenas a assinatura.

    A analise de imagem precisa conseguir abrir o arquivo. Um cabecalho solto
    seria reconhecido pela tabela de assinaturas, mas o Pillow recusaria - e o
    teste estaria verificando a coisa errada.
    """
    buffer = io.BytesIO()
    Image.new("RGB", (120, 90), (10, 20, 30)).save(buffer, format="PNG")
    return buffer.getvalue()


def _build_jpeg_with_gps() -> bytes:
    """Gera um JPEG com EXIF de dispositivo e coordenadas GPS.

    As coordenadas sao as do exemplo da especificacao: 22 graus 7 minutos 12
    segundos Sul, 51 graus 23 minutos 24 segundos Oeste, que convertem para
    -22.12 e -51.39.
    """
    image = Image.new("RGB", (640, 480), (40, 80, 120))
    exif = image.getexif()
    exif[ExifTags.Base.Make.value] = "Apple"
    exif[ExifTags.Base.Model.value] = "iPhone 15 Pro"

    gps = exif.get_ifd(ExifTags.IFD.GPSInfo)
    gps[ExifTags.GPS.GPSLatitude.value] = (IFDRational(22), IFDRational(7), IFDRational(12))
    gps[ExifTags.GPS.GPSLatitudeRef.value] = "S"
    gps[ExifTags.GPS.GPSLongitude.value] = (IFDRational(51), IFDRational(23), IFDRational(24))
    gps[ExifTags.GPS.GPSLongitudeRef.value] = "W"

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", exif=exif)
    return buffer.getvalue()


def _build_decompression_bomb() -> bytes:
    """PNG minusculo cujo cabecalho declara 60.000 x 60.000 pixels.

    Montado a mao porque nenhuma biblioteca gera de boa vontade um arquivo
    cujo cabecalho mente sobre o conteudo.
    """

    def chunk(kind: bytes, data: bytes) -> bytes:
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 60_000, 60_000, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(b"\x00" * 16))
        + chunk(b"IEND", b"")
    )


PNG = _build_png()
JPEG_WITH_GPS = _build_jpeg_with_gps()
DECOMPRESSION_BOMB = _build_decompression_bomb()

# Bytes inofensivos com aparencia de dropper: comecam com a assinatura de
# executavel Windows e carregam strings tipicas de script malicioso.
# Nao executam nada - sao apenas dados.
FAKE_DROPPER = (
    b"MZ\x90\x00\x03\x00\x00\x00"
    b"This program cannot be run in DOS mode.\x00"
    b"powershell.exe -windowstyle hidden -EncodedCommand payload\x00"
    b"https://malicious.example.com/stage2.exe\x00"
    b"C:\\Users\\Public\\dropper.exe\x00"
    b"callback 203.0.113.45\x00"
)

EMAIL = (
    b"Return-Path: <financeiro@empresa.com>\r\n"
    b"From: Financeiro <financeiro@empresa.com>\r\n"
    b"To: vitima@empresa.com\r\n"
    b"Subject: Fatura em atraso\r\n"
    b"Date: Mon, 15 Oct 2026 09:12:00 -0300\r\n"
    b"\r\n"
    b"Segue a fatura em anexo.\r\n"
)


def post_evidence(client: TestClient, filename: str, content: bytes):
    """Envia um arquivo para a rota de analise."""
    return client.post("/analyze", files={"file": (filename, content, "application/octet-stream")})


class TestSuccessfulAnalysis:
    """Caminho feliz: arquivo legitimo, analise completa."""

    def test_responds_with_success(self, client: TestClient) -> None:
        assert post_evidence(client, "grafico.png", PNG).status_code == 200

    def test_returns_the_original_filename(self, client: TestClient) -> None:
        payload = post_evidence(client, "grafico.png", PNG).json()

        assert payload["filename"] == "grafico.png"

    def test_returns_every_hash(self, client: TestClient) -> None:
        hashes = post_evidence(client, "grafico.png", PNG).json()["file"]["hashes"]

        assert set(hashes) == {"md5", "sha1", "sha256", "sha512"}
        assert len(hashes["sha256"]) == 64

    def test_returns_size_and_entropy(self, client: TestClient) -> None:
        file_section = post_evidence(client, "grafico.png", PNG).json()["file"]

        assert file_section["size"] == len(PNG)
        assert 0.0 <= file_section["entropy"] <= 8.0

    def test_identifies_the_format(self, client: TestClient) -> None:
        detection = post_evidence(client, "grafico.png", PNG).json()["detection"]

        assert detection["detected_name"] == "PNG image"
        assert detection["detected_mime"] == "image/png"
        assert detection["evidence_type"] == "image"
        assert detection["mismatch"] == "none"

    def test_always_includes_the_disclaimer(self, client: TestClient) -> None:
        """O relatorio nunca sai sem o aviso de que e triagem heuristica."""
        payload = post_evidence(client, "grafico.png", PNG).json()

        assert "does not provide a definitive malware" in payload["disclaimer"]


class TestDisguisedExecutable:
    """O cenario que motiva o projeto inteiro."""

    def test_reports_the_mismatch(self, client: TestClient) -> None:
        detection = post_evidence(client, "invoice.jpg", FAKE_DROPPER).json()["detection"]

        assert detection["mismatch"] == "executable_disguised"
        assert detection["declared_extension"] == ".jpg"
        assert detection["detected_category"] == "executable"

    def test_reports_the_artifacts_found_inside(self, client: TestClient) -> None:
        artifacts = post_evidence(client, "invoice.jpg", FAKE_DROPPER).json()["strings"][
            "artifacts"
        ]

        assert "powershell.exe" in artifacts["suspicious_keywords"]
        assert "https://malicious.example.com/stage2.exe" in artifacts["urls"]
        assert "203.0.113.45" in artifacts["ipv4"]


class TestRiskScore:
    """O score e os indicadores na resposta da API."""

    def test_clean_file_scores_zero_and_low(self, client: TestClient) -> None:
        """Nenhum achado significa "nada chamou atencao", nao "e seguro"."""
        risk = post_evidence(client, "grafico.png", PNG).json()["risk"]

        assert risk["score"] == 0
        assert risk["level"] == "low"
        assert risk["indicators"] == []

    def test_disguised_executable_reaches_critical(self, client: TestClient) -> None:
        """O caso documentado na especificacao, agora ponta a ponta.

        Mismatch de extensao (35) + executavel disfarcado (50) + comandos
        suspeitos (20) = 100, limitado ao maximo.
        """
        risk = post_evidence(client, "invoice.jpg", FAKE_DROPPER).json()["risk"]

        assert risk["level"] == "critical"
        assert risk["score"] >= 76

        ids = [indicator["id"] for indicator in risk["indicators"]]
        assert "file.extension_mismatch" in ids
        assert "file.executable_disguised" in ids

    def test_every_indicator_explains_itself(self, client: TestClient) -> None:
        """Cada indicador traz id, titulo, descricao, severidade e evidencia.

        Sem isso o score seria um numero que ninguem consegue defender.
        """
        indicators = post_evidence(client, "invoice.jpg", FAKE_DROPPER).json()["risk"][
            "indicators"
        ]

        assert indicators

        for indicator in indicators:
            assert indicator["id"]
            assert indicator["title"]
            assert indicator["description"]
            assert indicator["severity"] in {"info", "low", "medium", "high", "critical"}
            assert isinstance(indicator["score"], int)
            assert "evidence" in indicator

    def test_the_evidence_shows_both_sides_of_the_mismatch(self, client: TestClient) -> None:
        indicators = post_evidence(client, "invoice.jpg", FAKE_DROPPER).json()["risk"][
            "indicators"
        ]

        mismatch = next(item for item in indicators if item["id"] == "file.extension_mismatch")

        assert mismatch["evidence"]["declared_extension"] == ".jpg"
        assert "Windows executable" in mismatch["evidence"]["detected_type"]

    def test_the_score_never_exceeds_one_hundred(self, client: TestClient) -> None:
        risk = post_evidence(client, "invoice.jpg", FAKE_DROPPER).json()["risk"]

        assert 0 <= risk["score"] <= 100


class TestImageAnalysis:
    """A secao de imagem so aparece quando a evidencia e uma imagem."""

    def test_image_section_is_present_for_images(self, client: TestClient) -> None:
        payload = post_evidence(client, "grafico.png", PNG).json()

        assert payload["image"] is not None
        assert payload["image"]["image_format"] == "PNG"
        assert payload["image"]["width"] == 120
        assert payload["image"]["height"] == 90

    def test_image_section_is_absent_for_other_evidence(self, client: TestClient) -> None:
        """Campo ausente em vez de objeto cheio de nulos."""
        payload = post_evidence(client, "notas.txt", PLAIN_TEXT).json()

        assert payload["image"] is None

    def test_exif_and_gps_reach_the_response(self, client: TestClient) -> None:
        """Metadados da foto chegam ate o JSON, prontos para a interface."""
        payload = post_evidence(client, "ferias.jpg", JPEG_WITH_GPS).json()

        image = payload["image"]

        assert image["device_make"] == "Apple"
        assert image["device_model"] == "iPhone 15 Pro"
        assert image["gps"]["latitude"] == pytest.approx(-22.12)
        assert image["gps"]["longitude"] == pytest.approx(-51.39)

    def test_gps_raises_an_informational_indicator(self, client: TestClient) -> None:
        """Localizacao avisa sem pontuar: e privacidade, nao risco."""
        payload = post_evidence(client, "ferias.jpg", JPEG_WITH_GPS).json()

        gps_indicator = next(
            item for item in payload["risk"]["indicators"] if item["id"] == "image.gps_coordinates"
        )

        assert gps_indicator["score"] == 0
        assert gps_indicator["severity"] == "info"
        assert payload["risk"]["level"] == "low"

    def test_decompression_bomb_is_detected_safely(self, client: TestClient) -> None:
        """Um arquivo de 68 bytes que declara 3,6 bilhoes de pixels.

        O teste so termina porque a analise NUNCA decodifica os pixels. Se
        decodificasse, tentaria alocar mais de 14 GB de memoria.
        """
        payload = post_evidence(client, "inofensiva.png", DECOMPRESSION_BOMB).json()

        ids = [item["id"] for item in payload["risk"]["indicators"]]

        assert "image.decompression_bomb" in ids


def _build_phishing_email() -> bytes:
    """Monta um phishing completo, com tudo o que a Etapa 7 reconhece.

    Nada aqui e executavel de verdade: o anexo sao apenas os bytes `MZ`
    seguidos de texto. O que importa e que ele se apresenta como PDF.
    """
    message = EmailMessage()
    message["From"] = "Financeiro <financeiro@empresa.com>"
    message["To"] = "vitima@empresa.com"
    message["Subject"] = "Fatura em atraso - acao necessaria"
    message["Date"] = "Mon, 15 Oct 2026 09:12:00 -0300"
    message["Reply-To"] = "empresa-financeiro@gmail.com"
    message["Return-Path"] = "<bounce@servidor-desconhecido.ru>"
    message["Authentication-Results"] = (
        "mx.empresa.com; spf=fail (sender IP is 203.0.113.9); "
        "dkim=fail header.i=@empresa.com; dmarc=fail (p=REJECT)"
    )

    message.set_content("Segue a fatura em anexo. Regularize ate hoje.")
    message.add_alternative(
        '<p>Acesse <a href="http://203.0.113.45/login">www.empresa.com.br</a> '
        "para regularizar.</p>",
        subtype="html",
    )

    message.add_attachment(
        b"MZ\x90\x00\x03\x00\x00\x00This program cannot be run in DOS mode.",
        maintype="application",
        subtype="pdf",
        filename="fatura.pdf",
    )

    return message.as_bytes()


PHISHING_EMAIL = _build_phishing_email()


class TestEmailAnalysis:
    """A secao de e-mail e a analise recursiva dos anexos."""

    def test_email_section_is_present_for_emails(self, client: TestClient) -> None:
        payload = post_evidence(client, "mensagem.eml", EMAIL).json()

        assert payload["email"] is not None
        assert payload["email"]["from_domain"] == "empresa.com"

    def test_email_section_is_absent_for_other_evidence(self, client: TestClient) -> None:
        assert post_evidence(client, "grafico.png", PNG).json()["email"] is None

    def test_authentication_failures_become_indicators(self, client: TestClient) -> None:
        payload = post_evidence(client, "phishing.eml", PHISHING_EMAIL).json()

        ids = [item["id"] for item in payload["risk"]["indicators"]]

        assert "email.spf_failed" in ids
        assert "email.dkim_failed" in ids
        assert "email.dmarc_failed" in ids

    def test_sender_mismatches_become_indicators(self, client: TestClient) -> None:
        payload = post_evidence(client, "phishing.eml", PHISHING_EMAIL).json()

        ids = [item["id"] for item in payload["risk"]["indicators"]]

        assert "email.reply_to_mismatch" in ids
        assert "email.return_path_mismatch" in ids

    def test_misleading_link_becomes_an_indicator(self, client: TestClient) -> None:
        """O link mostra empresa.com.br e aponta para um IP."""
        payload = post_evidence(client, "phishing.eml", PHISHING_EMAIL).json()

        indicator = next(
            item
            for item in payload["risk"]["indicators"]
            if item["id"] == "email.misleading_link"
        )

        assert indicator["evidence"]["links"][0]["displayed"] == "www.empresa.com.br"
        assert "203.0.113.45" in indicator["evidence"]["links"][0]["destination"]

    def test_attachment_is_analysed_recursively(self, client: TestClient) -> None:
        """O anexo passa pelo mesmo pipeline do arquivo principal.

        Um `fatura.pdf` cujos bytes comecam com `MZ` recebe a sua propria
        nota, dentro do relatorio do e-mail.
        """
        payload = post_evidence(client, "phishing.eml", PHISHING_EMAIL).json()

        attachment = payload["email"]["attachments"][0]

        assert attachment["filename"] == "fatura.pdf"
        assert attachment["declared_content_type"] == "application/pdf"
        assert attachment["analysis"] is not None
        assert attachment["analysis"]["detection"]["mismatch"] == "executable_disguised"
        assert attachment["analysis"]["risk"]["level"] == "critical"

    def test_executable_attachment_raises_an_indicator_on_the_message(
        self, client: TestClient
    ) -> None:
        """O e-mail carrega a culpa do anexo, alem do anexo ter a sua."""
        payload = post_evidence(client, "phishing.eml", PHISHING_EMAIL).json()

        indicator = next(
            item
            for item in payload["risk"]["indicators"]
            if item["id"] == "email.executable_attachment"
        )

        assert indicator["evidence"]["attachments"] == ["fatura.pdf"]

    def test_the_whole_message_scores_critical(self, client: TestClient) -> None:
        payload = post_evidence(client, "phishing.eml", PHISHING_EMAIL).json()

        assert payload["risk"]["level"] == "critical"

    def test_an_ordinary_email_scores_low(self, client: TestClient) -> None:
        """O contraponto: mensagem comum nao pode gerar alarme."""
        payload = post_evidence(client, "mensagem.eml", EMAIL).json()

        assert payload["risk"]["score"] == 0
        assert payload["risk"]["level"] == "low"


class TestEvidenceRouting:
    """O tipo de evidencia reportado guia os analisadores das proximas etapas."""

    def test_email_is_recognised_despite_the_extension(self, client: TestClient) -> None:
        detection = post_evidence(client, "fatura.txt", EMAIL).json()["detection"]

        assert detection["evidence_type"] == "email"

    def test_unknown_content_is_reported_honestly(self, client: TestClient) -> None:
        detection = post_evidence(client, "notas.txt", PLAIN_TEXT).json()["detection"]

        assert detection["detected_name"] is None
        assert detection["mismatch"] == "none"


class TestStringsPayload:
    """A resposta traz artefatos completos e uma amostra das strings."""

    def test_reports_the_total_and_the_returned_count(self, client: TestClient) -> None:
        strings = post_evidence(client, "dropper.bin", FAKE_DROPPER).json()["strings"]

        assert strings["total"] >= strings["returned"]
        assert len(strings["sample"]) == strings["returned"]

    def test_the_uploaded_evidence_gets_the_full_listing(self, client: TestClient) -> None:
        """A evidencia principal vem com a lista completa, nao com uma amostra.

        E o que permite a interface oferecer busca. Uma amostra de 200 tirada
        de milhares seria inutil: quem analisa nao escolheu aquelas 200, e
        procurar algo especifico nelas vira sorte.
        """
        many = b"".join(f"string-numero-{index}\x00".encode() for index in range(1000))

        strings = post_evidence(client, "muitas.bin", many).json()["strings"]

        assert strings["returned"] == strings["total"] == 1000
        assert strings["truncated"] is False
        assert strings["truncation_reason"] is None

    def test_the_total_is_the_real_count(self, client: TestClient) -> None:
        """O total conta as strings de verdade, nao o tamanho da lista devolvida."""
        many = b"".join(f"string-numero-{index}\x00".encode() for index in range(1000))

        strings = post_evidence(client, "muitas.bin", many).json()["strings"]

        assert strings["total"] == 1000

    def test_small_file_is_not_marked_as_truncated(self, client: TestClient) -> None:
        strings = post_evidence(client, "grafico.png", PNG).json()["strings"]

        assert strings["truncated"] is False


class TestUploadLimits:
    """Protecao contra upload grande demais."""

    def test_rejects_a_file_over_the_limit(self, client: TestClient, monkeypatch) -> None:
        """Passar do limite devolve 413, nao 500."""
        from app.config import get_settings

        settings = get_settings()
        monkeypatch.setattr(settings, "max_upload_size", 1024)

        response = post_evidence(client, "huge.bin", b"A" * 4096)

        assert response.status_code == 413
        assert "1024" in response.json()["detail"]

    def test_rejects_a_request_without_a_file(self, client: TestClient) -> None:
        """Requisicao mal formada e erro de validacao, nao falha interna."""
        assert client.post("/analyze").status_code == 422


class TestEdgeCases:
    """Entradas incomuns que nao podem derrubar a rota."""

    def test_empty_file_is_analysed(self, client: TestClient) -> None:
        payload = post_evidence(client, "vazio.bin", b"").json()

        assert payload["file"]["size"] == 0
        assert payload["file"]["entropy"] == 0.0
        assert payload["detection"]["detected_name"] is None

    def test_filename_with_path_traversal_is_not_used_as_a_path(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        """Um nome hostil nao vira caminho em disco.

        A extensao continua sendo auditada - e `.exe` sobre bytes de PNG e um
        mismatch legitimo - mas nada e gravado fora da pasta de trabalho.
        """
        response = post_evidence(client, r"..\..\Windows\System32\evil.exe", PNG)

        assert response.status_code == 200
        assert response.json()["detection"]["declared_extension"] == ".exe"

    def test_filename_without_extension_is_handled(self, client: TestClient) -> None:
        detection = post_evidence(client, "Makefile", PLAIN_TEXT).json()["detection"]

        assert detection["declared_extension"] == ""
        assert detection["mismatch"] == "none"


class TestNoPersistence:
    """A promessa central do projeto: nada fica guardado."""

    def test_the_working_directory_is_empty_after_analysis(self, client: TestClient) -> None:
        """Depois de varias analises, nenhum temporario sobra em disco."""
        from app.config import get_settings

        temp_dir = get_settings().temp_dir

        for index in range(5):
            assert post_evidence(client, f"evidencia-{index}.png", PNG).status_code == 200

        # A pasta pode nem existir, se nenhuma analise precisou cria-la.
        leftovers = list(temp_dir.iterdir()) if temp_dir.exists() else []

        assert leftovers == []


class TestApiDocumentation:
    """A rota aparece documentada automaticamente."""

    def test_analyze_route_is_in_the_openapi_schema(self, client: TestClient) -> None:
        schema = client.get("/openapi.json").json()

        assert "/analyze" in schema["paths"]
        assert "post" in schema["paths"]["/analyze"]
