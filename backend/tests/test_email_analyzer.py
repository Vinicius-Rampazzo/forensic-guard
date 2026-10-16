"""Testes da analise de e-mail.

As mensagens sao montadas em codigo, com os cabecalhos escritos linha a linha.
Isso mantem a fixture legivel: da para ver no proprio teste exatamente qual
cabecalho esta sendo exercitado.
"""

from email.message import EmailMessage
from pathlib import Path

from app.analyzers.email_analyzer import (
    MAX_ATTACHMENTS,
    analyze_email,
)


def write_eml(path: Path, raw: str) -> Path:
    """Grava uma mensagem escrita a mao."""
    path.write_bytes(raw.encode("utf-8"))
    return path


def build_message(
    *,
    sender: str = "Financeiro <financeiro@empresa.com>",
    reply_to: str | None = None,
    return_path: str | None = None,
    authentication: str | None = None,
    html: str | None = None,
    text: str = "Segue a fatura em anexo.",
    attachments: tuple[tuple[str, bytes, str], ...] = (),
) -> EmailMessage:
    """Monta uma mensagem com os cabecalhos e partes pedidos."""
    message = EmailMessage()
    message["From"] = sender
    message["To"] = "vitima@empresa.com"
    message["Subject"] = "Fatura em atraso"
    message["Date"] = "Mon, 15 Oct 2026 09:12:00 -0300"
    message["Message-ID"] = "<abc123@empresa.com>"

    if reply_to:
        message["Reply-To"] = reply_to
    if return_path:
        message["Return-Path"] = return_path
    if authentication:
        message["Authentication-Results"] = authentication

    message.set_content(text)

    if html:
        message.add_alternative(html, subtype="html")

    for filename, payload, mime in attachments:
        maintype, subtype = mime.split("/", 1)
        message.add_attachment(
            payload, maintype=maintype, subtype=subtype, filename=filename
        )

    return message


def write_message(path: Path, message: EmailMessage) -> Path:
    path.write_bytes(message.as_bytes())
    return path


class TestHeaders:
    """Leitura dos cabecalhos principais."""

    def test_reads_the_main_headers(self, tmp_path: Path) -> None:
        path = write_message(tmp_path / "msg.eml", build_message())

        result = analyze_email(path)

        assert result.headers["Subject"] == "Fatura em atraso"
        assert result.headers["To"] == "vitima@empresa.com"
        assert result.from_address == "financeiro@empresa.com"
        assert result.from_domain == "empresa.com"

    def test_decodes_mime_encoded_subjects(self, tmp_path: Path) -> None:
        """Assuntos com acentuacao trafegam codificados.

        Sem decodificar, o relatorio exibiria `=?utf-8?B?...?=` em vez do
        texto - inutil para quem le.
        """
        raw = (
            "From: a@b.com\r\n"
            "To: c@d.com\r\n"
            "Subject: =?utf-8?B?RmF0dXJhIGVtIGF0cmFzbw==?=\r\n"
            "\r\n"
            "corpo\r\n"
        )

        result = analyze_email(write_eml(tmp_path / "msg.eml", raw))

        assert result.headers["Subject"] == "Fatura em atraso"

    def test_collects_the_received_chain(self, tmp_path: Path) -> None:
        """Received e um dos poucos cabecalhos que o remetente nao escreve."""
        raw = (
            "Received: from mx2.empresa.com by mx1.empresa.com\r\n"
            "Received: from origem.example by mx2.empresa.com\r\n"
            "From: a@b.com\r\n"
            "\r\n"
            "corpo\r\n"
        )

        result = analyze_email(write_eml(tmp_path / "msg.eml", raw))

        assert len(result.received_chain) == 2

    def test_missing_headers_are_not_errors(self, tmp_path: Path) -> None:
        """Mensagem minima continua sendo analisavel."""
        result = analyze_email(write_eml(tmp_path / "msg.eml", "From: a@b.com\r\n\r\nola\r\n"))

        assert result.error is None
        assert result.reply_to is None
        assert result.reply_to_mismatch is False


class TestSenderMismatch:
    """Comparacao entre os dominios dos cabecalhos de remetente."""

    def test_detects_reply_to_pointing_elsewhere(self, tmp_path: Path) -> None:
        """O exemplo da especificacao.

        A mensagem se diz da empresa, mas a resposta iria para um Gmail.
        """
        message = build_message(
            sender="Financeiro <financeiro@empresa.com>",
            reply_to="empresa-financeiro@gmail.com",
        )

        result = analyze_email(write_message(tmp_path / "msg.eml", message))

        assert result.reply_to_mismatch is True
        assert result.from_domain == "empresa.com"
        assert result.reply_to_domain == "gmail.com"

    def test_same_domain_is_not_a_mismatch(self, tmp_path: Path) -> None:
        message = build_message(reply_to="suporte@empresa.com")

        result = analyze_email(write_message(tmp_path / "msg.eml", message))

        assert result.reply_to_mismatch is False

    def test_www_prefix_is_ignored_in_the_comparison(self, tmp_path: Path) -> None:
        message = build_message(sender="a@empresa.com", reply_to="b@www.empresa.com")

        result = analyze_email(write_message(tmp_path / "msg.eml", message))

        assert result.reply_to_mismatch is False

    def test_missing_reply_to_is_not_a_mismatch(self, tmp_path: Path) -> None:
        """Ausencia de cabecalho nao e contradicao."""
        result = analyze_email(write_message(tmp_path / "msg.eml", build_message()))

        assert result.reply_to_mismatch is False

    def test_detects_return_path_pointing_elsewhere(self, tmp_path: Path) -> None:
        message = build_message(return_path="<bounces@plataforma-marketing.com>")

        result = analyze_email(write_message(tmp_path / "msg.eml", message))

        assert result.return_path_mismatch is True


class TestAuthentication:
    """Leitura do veredito de SPF, DKIM e DMARC."""

    def test_reads_all_three_results(self, tmp_path: Path) -> None:
        message = build_message(
            authentication=(
                "mx.google.com; spf=fail (sender IP is 203.0.113.9); "
                "dkim=fail header.i=@empresa.com; dmarc=fail (p=REJECT)"
            )
        )

        auth = analyze_email(write_message(tmp_path / "msg.eml", message)).authentication

        assert auth.spf == "fail"
        assert auth.dkim == "fail"
        assert auth.dmarc == "fail"
        assert auth.spf_failed and auth.dkim_failed and auth.dmarc_failed

    def test_pass_results_are_not_failures(self, tmp_path: Path) -> None:
        message = build_message(authentication="mx.google.com; spf=pass; dkim=pass; dmarc=pass")

        auth = analyze_email(write_message(tmp_path / "msg.eml", message)).authentication

        assert auth.spf == "pass"
        assert not auth.spf_failed
        assert not auth.dkim_failed
        assert not auth.dmarc_failed

    def test_none_is_not_a_failure(self, tmp_path: Path) -> None:
        """`none` significa que o dominio nao publicou politica.

        E omissao do dominio, nao sinal de falsificacao - tratar como falha
        marcaria metade da internet.
        """
        message = build_message(authentication="mx.google.com; dmarc=none")

        auth = analyze_email(write_message(tmp_path / "msg.eml", message)).authentication

        assert auth.dmarc == "none"
        assert not auth.dmarc_failed

    def test_softfail_counts_as_failure(self, tmp_path: Path) -> None:
        message = build_message(authentication="mx.google.com; spf=softfail")

        auth = analyze_email(write_message(tmp_path / "msg.eml", message)).authentication

        assert auth.spf_failed

    def test_missing_header_leaves_everything_unknown(self, tmp_path: Path) -> None:
        """Nao ter resultado e diferente de ter falhado.

        Um .eml exportado antes da entrega nunca passou por um verificador.
        """
        auth = analyze_email(
            write_message(tmp_path / "msg.eml", build_message())
        ).authentication

        assert auth.spf is None
        assert not auth.spf_failed

    def test_falls_back_to_received_spf(self, tmp_path: Path) -> None:
        """Alguns servidores gravam apenas o Received-SPF."""
        raw = (
            "Received-SPF: Fail (mx.example: domain does not designate)\r\n"
            "From: a@b.com\r\n"
            "\r\n"
            "corpo\r\n"
        )

        auth = analyze_email(write_eml(tmp_path / "msg.eml", raw)).authentication

        assert auth.spf == "fail"
        assert auth.spf_failed


class TestLinks:
    """Extracao de links do corpo HTML."""

    def test_detects_a_misleading_link(self, tmp_path: Path) -> None:
        """A tecnica que define o phishing.

        O texto mostra o banco, o destino e outro lugar. Nem o texto nem a
        URL, isolados, revelam o problema.
        """
        html = '<p><a href="http://evil.example/login">www.banco.com.br</a></p>'
        message = build_message(html=html)

        result = analyze_email(write_message(tmp_path / "msg.eml", message))

        assert len(result.misleading_links) == 1
        assert result.misleading_links[0].display_text == "www.banco.com.br"
        assert result.misleading_links[0].url == "http://evil.example/login"

    def test_an_honest_link_is_not_misleading(self, tmp_path: Path) -> None:
        html = '<a href="https://www.banco.com.br/acesso">www.banco.com.br</a>'
        message = build_message(html=html)

        result = analyze_email(write_message(tmp_path / "msg.eml", message))

        assert result.misleading_links == ()

    def test_a_subdomain_of_the_displayed_domain_is_not_misleading(self, tmp_path: Path) -> None:
        """Falso positivo mais comum, evitado de proposito."""
        html = '<a href="https://login.banco.com.br/x">banco.com.br</a>'
        message = build_message(html=html)

        assert analyze_email(write_message(tmp_path / "msg.eml", message)).misleading_links == ()

    def test_link_without_a_domain_in_the_text_is_not_misleading(self, tmp_path: Path) -> None:
        """"Clique aqui" nao afirma destino nenhum, entao nao pode mentir."""
        html = '<a href="http://evil.example/x">Clique aqui para ver a fatura</a>'
        message = build_message(html=html)

        assert analyze_email(write_message(tmp_path / "msg.eml", message)).misleading_links == ()

    def test_collects_urls_from_both_bodies(self, tmp_path: Path) -> None:
        message = build_message(
            text="acesse https://exemplo.com/texto",
            html='<a href="https://exemplo.com/html">clique</a>',
        )

        result = analyze_email(write_message(tmp_path / "msg.eml", message))

        assert "https://exemplo.com/texto" in result.urls
        assert "https://exemplo.com/html" in result.urls

    def test_malformed_html_does_not_break_the_analysis(self, tmp_path: Path) -> None:
        message = build_message(html='<a href="http://x.com">sem fechar <p><div')

        assert analyze_email(write_message(tmp_path / "msg.eml", message)).error is None


class TestAttachments:
    """Extracao dos anexos."""

    def test_extracts_an_attachment(self, tmp_path: Path) -> None:
        message = build_message(
            attachments=(("fatura.pdf", b"%PDF-1.7\nconteudo", "application/pdf"),)
        )

        result = analyze_email(write_message(tmp_path / "msg.eml", message))

        assert len(result.attachments) == 1
        assert result.attachments[0].filename == "fatura.pdf"
        assert result.attachments[0].declared_content_type == "application/pdf"
        assert result.attachments[0].payload.startswith(b"%PDF")

    def test_extracts_several_attachments(self, tmp_path: Path) -> None:
        message = build_message(
            attachments=(
                ("fatura.pdf", b"%PDF-1.7", "application/pdf"),
                ("logo.png", b"\x89PNG\r\n\x1a\n", "image/png"),
            )
        )

        result = analyze_email(write_message(tmp_path / "msg.eml", message))

        assert [item.filename for item in result.attachments] == ["fatura.pdf", "logo.png"]

    def test_stops_at_the_attachment_limit(self, tmp_path: Path) -> None:
        """Vinte anexos ja e muito mais do que mensagem legitima carrega."""
        many = tuple(
            (f"arquivo-{index}.txt", b"conteudo", "text/plain")
            for index in range(MAX_ATTACHMENTS + 5)
        )
        message = build_message(attachments=many)

        result = analyze_email(write_message(tmp_path / "msg.eml", message))

        assert len(result.attachments) == MAX_ATTACHMENTS
        assert result.attachments_truncated is True

    def test_message_without_attachments(self, tmp_path: Path) -> None:
        result = analyze_email(write_message(tmp_path / "msg.eml", build_message()))

        assert result.attachments == ()
        assert result.attachments_truncated is False


class TestHostileInput:
    """Mensagens malformadas nao podem derrubar a analise."""

    def test_empty_file_is_handled(self, tmp_path: Path) -> None:
        result = analyze_email(write_eml(tmp_path / "vazio.eml", ""))

        assert result.error is None or result.from_address is None

    def test_binary_garbage_is_handled(self, tmp_path: Path) -> None:
        path = tmp_path / "lixo.eml"
        path.write_bytes(bytes(range(256)) * 10)

        result = analyze_email(path)

        assert result.from_address is None

    def test_missing_file_returns_an_error(self, tmp_path: Path) -> None:
        assert analyze_email(tmp_path / "nao-existe.eml").error is not None

    def test_oversized_message_is_refused_before_parsing(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """O teto existe porque o parser carrega a mensagem inteira na memoria.

        E o unico ponto do projeto que nao le em blocos. Com o limite geral de
        upload em 1 GB, sem este teto um unico `.eml` consumiria essa memoria
        toda - e duas analises simultaneas derrubariam o servico.

        A verificacao acontece ANTES de abrir o arquivo: depois que o parser
        comeca, a memoria ja foi comprometida.
        """
        from app.analyzers import email_analyzer

        monkeypatch.setattr(email_analyzer, "MAX_EMAIL_BYTES", 100)

        path = write_eml(tmp_path / "grande.eml", "From: a@b.com\r\n\r\n" + "x" * 500)

        result = analyze_email(path)

        assert result.error is not None
        assert "limit for message parsing" in result.error
        # Nada foi parseado: a recusa aconteceu antes.
        assert result.from_address is None

    def test_unknown_charset_does_not_break_decoding(self, tmp_path: Path) -> None:
        """Charset inventado e caso comum em mensagem forjada."""
        raw = (
            "From: a@b.com\r\n"
            "Content-Type: text/plain; charset=nao-existe-123\r\n"
            "\r\n"
            "corpo da mensagem\r\n"
        )

        result = analyze_email(write_eml(tmp_path / "msg.eml", raw))

        assert result.error is None
        assert result.has_text_body is True
