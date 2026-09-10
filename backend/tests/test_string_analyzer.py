"""Testes da extracao de strings e artefatos.

As fixtures sao construidas em codigo, byte a byte. Nenhum binario entra no
repositorio - regra do projeto e boa pratica de seguranca: ninguem deve baixar
um arquivo suspeito ao clonar uma ferramenta forense.
"""

from pathlib import Path

from app.analyzers.string_analyzer import (
    MAX_SCAN_BYTES,
    analyze_strings,
    extract_artifacts,
    extract_ascii_strings,
    extract_strings,
    extract_utf16_strings,
)


class TestAsciiExtraction:
    """Separacao de texto legivel ASCII do ruido binario."""

    def test_separates_text_from_surrounding_binary_noise(self) -> None:
        """Bytes de controle interrompem a sequencia; o texto sobra."""
        data = b"\x00\x01\x02ForensicGuard\xff\xfe\x00analysis\x00"

        assert extract_ascii_strings(data) == ["ForensicGuard", "analysis"]

    def test_discards_sequences_shorter_than_the_minimum(self) -> None:
        """Sequencias curtas sao ruido: em dados binarios surgem por acaso."""
        data = b"\x00ab\x00cde\x00LONGENOUGH\x00"

        assert extract_ascii_strings(data) == ["LONGENOUGH"]

    def test_minimum_length_is_configurable(self) -> None:
        """Baixar o minimo faz aparecer sequencias antes descartadas."""
        data = b"\x00ab\x00cde\x00"

        assert extract_ascii_strings(data, min_length=2) == ["ab", "cde"]


class TestUtf16Extraction:
    """Extracao do formato usado pela maioria dos binarios do Windows."""

    def test_finds_utf16_text(self) -> None:
        """Strings gravadas em UTF-16LE sao reconhecidas."""
        data = b"\x00\x00" + "C:\\Windows\\System32".encode("utf-16-le") + b"\x00\x00"

        assert "C:\\Windows\\System32" in extract_utf16_strings(data)

    def test_utf16_text_is_invisible_to_the_ascii_extractor(self) -> None:
        """Justifica a existencia das duas tecnicas de extracao.

        Em UTF-16LE cada caractere vem seguido de um byte nulo, que interrompe
        a sequencia ASCII. Sem o extrator especifico, a maior parte das strings
        de um executavel do Windows passaria despercebida.
        """
        data = "powershell.exe".encode("utf-16-le")

        assert extract_ascii_strings(data) == []
        assert extract_utf16_strings(data) == ["powershell.exe"]

    def test_a_match_can_absorb_the_preceding_character(self) -> None:
        """Documenta uma limitacao conhecida e aceita.

        Quando texto ASCII e seguido de um byte nulo, o ultimo caractere dele
        mais esse nulo ja formam um par valido no formato UTF-16LE. O casamento
        comeca ali e absorve o caractere anterior.

        Nao ha como evitar: arquivos binarios nao garantem alinhamento, entao
        nao existe forma confiavel de saber onde uma sequencia UTF-16 comeca. O
        `strings -el` do Linux se comporta da mesma maneira.

        O impacto pratico e baixo, porque a extracao de artefatos usa fronteira
        de palavra e prefixos de protocolo. Este teste existe para que a
        limitacao seja decisao registrada, e nao surpresa para quem mexer aqui.
        """
        data = b"ForensicGuard\x00" + "payload".encode("utf-16-le")

        assert extract_utf16_strings(data) == ["dpayload"]


class TestCombinedExtraction:
    """Uniao das duas tecnicas, sem repeticao."""

    def test_removes_duplicates_and_keeps_the_order_of_appearance(self) -> None:
        """A mesma string repetida aparece uma vez so."""
        data = b"\x00ForensicGuard\x00analysis\x00ForensicGuard\x00"

        assert extract_strings(data) == ["ForensicGuard", "analysis"]


class TestArtifactExtraction:
    """Reconhecimento de padroes de interesse forense nas strings."""

    def test_finds_urls(self) -> None:
        strings = ["visit https://evil.example.com/payload.bin now", "nothing here"]

        assert extract_artifacts(strings)["urls"] == ["https://evil.example.com/payload.bin"]

    def test_finds_valid_ipv4_addresses(self) -> None:
        strings = ["connect to 192.168.1.10 and 8.8.8.8"]

        assert extract_artifacts(strings)["ipv4"] == ["192.168.1.10", "8.8.8.8"]

    def test_rejects_impossible_ipv4_addresses(self) -> None:
        """A validacao semantica e do modulo ipaddress, nao do regex.

        "999.999.999.999" tem forma de IPv4 mas nao e um endereco valido.
        """
        strings = ["999.999.999.999 and 256.1.1.1 are not addresses"]

        assert "ipv4" not in extract_artifacts(strings)

    def test_finds_ipv6_addresses(self) -> None:
        strings = ["server at 2001:0db8:85a3:0000:0000:8a2e:0370:7334 responded"]

        assert "2001:0db8:85a3:0000:0000:8a2e:0370:7334" in extract_artifacts(strings)["ipv6"]

    def test_does_not_confuse_a_timestamp_with_an_ipv6_address(self) -> None:
        """12:34:56 tem dois-pontos, mas nao e um endereco valido."""
        strings = ["backup finished at 12:34:56 today"]

        assert "ipv6" not in extract_artifacts(strings)

    def test_finds_emails(self) -> None:
        strings = ["contact security@empresa.com for details"]

        assert extract_artifacts(strings)["emails"] == ["security@empresa.com"]

    def test_finds_windows_paths(self) -> None:
        strings = [r"drops payload to C:\Users\Public\update.exe"]

        assert extract_artifacts(strings)["windows_paths"] == [r"C:\Users\Public\update.exe"]

    def test_finds_suspicious_keywords_ignoring_case(self) -> None:
        """Ofuscacao simples alterna a caixa das letras para escapar de buscas."""
        strings = ["PowerShell.EXE -EncodedCommand aGVsbG8="]

        keywords = extract_artifacts(strings)["suspicious_keywords"]

        assert "powershell.exe" in keywords
        assert "-encodedcommand" in keywords

    def test_omits_categories_without_any_match(self) -> None:
        """Relatorio nao deve ficar cheio de listas vazias."""
        assert extract_artifacts(["just some harmless text here"]) == {}

    def test_deduplicates_repeated_artifacts(self) -> None:
        strings = ["8.8.8.8", "8.8.8.8", "8.8.8.8"]

        assert extract_artifacts(strings)["ipv4"] == ["8.8.8.8"]


class TestFileAnalysis:
    """Analise completa, do arquivo em disco ao resultado."""

    def test_analyzes_a_suspicious_looking_file(self, tmp_path: Path) -> None:
        """Fixture segura: bytes inofensivos com aparencia de dropper."""
        evidence = tmp_path / "sample.bin"
        evidence.write_bytes(
            b"MZ\x90\x00"
            b"\x00\x00\x00"
            b"powershell.exe -windowstyle hidden -EncodedCommand payload\x00"
            b"https://malicious.example.com/stage2.exe\x00"
            b"C:\\Users\\Public\\dropper.exe\x00"
            b"callback 203.0.113.45\x00"
        )

        result = analyze_strings(evidence)

        assert not result.truncated
        assert "powershell.exe" in result.artifacts["suspicious_keywords"]
        assert "https://malicious.example.com/stage2.exe" in result.artifacts["urls"]
        assert "203.0.113.45" in result.artifacts["ipv4"]
        assert r"C:\Users\Public\dropper.exe" in result.artifacts["windows_paths"]

    def test_clean_file_produces_no_artifacts(self, tmp_path: Path) -> None:
        """Ausencia de artefato tambem precisa funcionar: nada de falso positivo."""
        evidence = tmp_path / "clean.txt"
        evidence.write_bytes(b"This is an ordinary text file about digital forensics.")

        result = analyze_strings(evidence)

        assert result.artifacts == {}
        assert not result.truncated
        assert result.strings

    def test_empty_file_is_handled(self, tmp_path: Path) -> None:
        """Arquivo vazio nao quebra a analise."""
        evidence = tmp_path / "empty.bin"
        evidence.write_bytes(b"")

        result = analyze_strings(evidence)

        assert result.strings == []
        assert result.artifacts == {}
        assert not result.truncated


class TestSafetyLimits:
    """Limites que impedem que uma evidencia grande esgote a memoria."""

    def test_oversized_file_is_truncated_and_reports_it(self, tmp_path: Path) -> None:
        """Passar do limite de leitura marca o resultado como parcial.

        Um relatorio forense nao pode dar a entender que examinou o arquivo
        inteiro quando examinou apenas o inicio dele.
        """
        evidence = tmp_path / "huge.bin"
        evidence.write_bytes(b"A" * (MAX_SCAN_BYTES + 1024))

        assert analyze_strings(evidence).truncated

    def test_file_exactly_at_the_limit_is_not_marked_as_truncated(self, tmp_path: Path) -> None:
        """Caso de fronteira: exatamente no limite ainda e analise completa."""
        evidence = tmp_path / "exact.bin"
        evidence.write_bytes(b"A" * MAX_SCAN_BYTES)

        assert not analyze_strings(evidence).truncated
