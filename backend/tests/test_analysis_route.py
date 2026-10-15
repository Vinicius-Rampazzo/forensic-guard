"""Testes da rota POST /analyze.

Testes de ponta a ponta: sobem um arquivo pelo cliente HTTP de teste e
verificam o JSON devolvido. Sao eles que provam que as pecas das Etapas 2 e 3
estao realmente costuradas.
"""

from pathlib import Path

from fastapi.testclient import TestClient

PADDING = b"\x00" * 64

PNG = b"\x89PNG\r\n\x1a\n" + PADDING
PLAIN_TEXT = b"Relatorio trimestral. Nada de especial aqui.\n" * 4

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

    def test_marks_the_sample_as_truncated_when_it_is(self, client: TestClient) -> None:
        """Relatorio parcial precisa se declarar parcial.

        O arquivo abaixo gera muito mais strings do que cabem na amostra.
        """
        many = b"".join(f"string-numero-{index}\x00".encode() for index in range(1000))

        strings = post_evidence(client, "muitas.bin", many).json()["strings"]

        assert strings["truncated"] is True
        assert strings["returned"] < strings["total"]

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
