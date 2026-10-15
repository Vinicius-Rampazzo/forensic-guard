"""Extracao de indicadores a partir dos fatos observados.

Papel na arquitetura
--------------------
    analise (hashes, entropia, strings, tipo)
            |
            v
    indicator_engine    <- aqui: traduz FATOS em INDICADORES
            |
            v
    risk_engine         soma os pesos e classifica

A separacao entre os dois ultimos existe porque eles mudam por motivos
diferentes. Os pesos sao calibrados com o tempo; a leitura dos fatos, nao. O
risk_engine nem sabe o que e entropia - ele so soma numeros.

Explicabilidade
---------------
Todo indicador carrega a **evidencia** que o disparou. Essa e a regra que
separa uma ferramenta forense util de um numero inventado: quem le o relatorio
precisa conseguir verificar a conclusao por conta propria, e discordar dela se
for o caso.

    score sem evidencia = opiniao
    score com evidencia = observacao verificavel
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.analyzers.email_analyzer import EmailAnalysis
from app.analyzers.file_analyzer import FileAnalysis
from app.analyzers.image_analyzer import MAX_SAFE_PIXELS, ImageAnalysis
from app.analyzers.url_analyzer import find_ip_address_urls, find_punycode_urls
from app.constants.risk_rules import (
    ANALYSIS_TRUNCATED,
    DECOMPRESSION_BOMB,
    DKIM_FAILED,
    DMARC_FAILED,
    EXECUTABLE_ATTACHMENT,
    EXECUTABLE_DISGUISED,
    EXTENSION_MISMATCH,
    GPS_COORDINATES,
    HIGH_ENTROPY_THRESHOLD,
    MISLEADING_LINK,
    NATURALLY_COMPRESSED_MIMES,
    REPLY_TO_MISMATCH,
    RETURN_PATH_MISMATCH,
    SPF_FAILED,
    SUSPICIOUS_COMMAND,
    UNEXPECTED_ENTROPY,
    URL_WITH_IP_HOST,
    URL_WITH_PUNYCODE,
    RiskRule,
)
from app.constants.signatures import FileCategory
from app.services.evidence_detector import EvidenceDetection, MismatchKind


@dataclass(frozen=True)
class Indicator:
    """Uma regra que disparou, com a evidencia que a justificou.

    Attributes:
        rule: a regra, com id, titulo, descricao, severidade e peso.
        evidence: os dados concretos que provocaram o disparo. Precisa ser
            serializavel em JSON, porque vai inteiro para a resposta da API.
    """

    rule: RiskRule
    evidence: dict[str, Any]


def collect_indicators(
    analysis: FileAnalysis,
    detection: EvidenceDetection,
    image: ImageAnalysis | None = None,
    email: EmailAnalysis | None = None,
    attachment_categories: tuple[tuple[str, FileCategory | None], ...] = (),
) -> list[Indicator]:
    """Reune todos os indicadores aplicaveis a uma evidencia.

    Args:
        analysis: fatos genericos do arquivo.
        detection: identidade da evidencia.
        image: analise de imagem, quando a evidencia for uma.
        email: analise de e-mail, quando a evidencia for uma.
        attachment_categories: nome e familia de cada anexo ja analisado.
            Vem de fora porque identificar o tipo de um anexo exige grava-lo
            em disco e roda-lo pela deteccao - trabalho do servico, nao deste
            modulo.

    A ordem e estavel: regras de arquivo, depois de conteudo, de URL, de
    imagem, de e-mail, e por fim as informativas. Resultado que muda de ordem
    sozinho e impossivel de testar e desconfortavel de ler.
    """
    return [
        *_mismatch_indicators(detection),
        *_entropy_indicators(analysis, detection),
        *_string_indicators(analysis),
        *_url_indicators(analysis),
        *_image_indicators(image, analysis.size),
        *_email_indicators(email),
        *_attachment_indicators(attachment_categories),
        *_truncation_indicators(analysis),
    ]


def _mismatch_indicators(detection: EvidenceDetection) -> list[Indicator]:
    """Indicadores derivados da contradicao entre nome e conteudo.

    Um executavel disfarcado dispara DUAS regras, e isso e proposital: ele e
    um mismatch de extensao (+35) E um executavel disfarcado (+50), somando
    85 - a faixa CRITICAL. Sao duas observacoes distintas sobre o mesmo fato,
    e cada uma aparece no relatorio com sua propria explicacao.
    """
    if detection.mismatch is MismatchKind.NONE:
        return []

    evidence = {
        "declared_extension": detection.declared_extension,
        "detected_type": detection.detected_name,
        "detected_mime": detection.detected_mime,
        "confirmed_bytes": detection.confirmed_bytes,
    }

    indicators = [Indicator(rule=EXTENSION_MISMATCH, evidence=evidence)]

    if detection.mismatch is MismatchKind.EXECUTABLE_DISGUISED:
        indicators.append(Indicator(rule=EXECUTABLE_DISGUISED, evidence=evidence))

    return indicators


def _entropy_indicators(
    analysis: FileAnalysis,
    detection: EvidenceDetection,
) -> list[Indicator]:
    """Indicador de entropia alta, apenas quando ela e inesperada.

    Arquivos compactados e de midia tem entropia alta por construcao. Marcar
    todos eles encheria o relatorio de ruido e ensinaria o usuario a ignorar o
    score - o pior resultado possivel para uma ferramenta de triagem.

    Num `.txt`, num documento ou num formato desconhecido, por outro lado, o
    mesmo valor e genuinamente estranho. Em executaveis tambem: ali sugere
    empacotamento, que e exatamente o que se quer observar.
    """
    if analysis.entropy <= HIGH_ENTROPY_THRESHOLD:
        return []

    if detection.detected_mime in NATURALLY_COMPRESSED_MIMES:
        return []

    return [
        Indicator(
            rule=UNEXPECTED_ENTROPY,
            evidence={
                "entropy": round(analysis.entropy, 4),
                "threshold": HIGH_ENTROPY_THRESHOLD,
                "detected_type": detection.detected_name,
            },
        )
    ]


def _string_indicators(analysis: FileAnalysis) -> list[Indicator]:
    """Indicador de referencias a interpretadores e tecnicas de execucao."""
    keywords = analysis.strings.artifacts.get("suspicious_keywords", [])

    if not keywords:
        return []

    return [Indicator(rule=SUSPICIOUS_COMMAND, evidence={"keywords": keywords})]


def _url_indicators(analysis: FileAnalysis) -> list[Indicator]:
    """Indicadores derivados das URLs encontradas no conteudo."""
    urls = analysis.strings.artifacts.get("urls", [])

    if not urls:
        return []

    indicators = []

    if ip_urls := find_ip_address_urls(urls):
        indicators.append(Indicator(rule=URL_WITH_IP_HOST, evidence={"urls": ip_urls}))

    if punycode_urls := find_punycode_urls(urls):
        indicators.append(Indicator(rule=URL_WITH_PUNYCODE, evidence={"urls": punycode_urls}))

    return indicators


def _image_indicators(image: ImageAnalysis | None, file_size: int) -> list[Indicator]:
    """Indicadores especificos de imagem.

    Repare no que NAO esta aqui: ausencia de EXIF e presenca de software de
    edicao. Nenhum dos dois vira indicador.

    Foto sem EXIF e o caso comum, nao o excepcional - toda rede social remove
    esses dados ao publicar. E "editada no Photoshop" descreve a maior parte
    das imagens profissionais do mundo. Transformar qualquer um dos dois em
    alerta encheria o relatorio de ruido.
    """
    if image is None:
        return []

    indicators = []

    if image.decompression_bomb:
        # As dimensoes nem sempre estao disponiveis: quando a protecao do
        # Pillow aborta ja na abertura, a leitura para antes de chegar nelas.
        # Por isso a evidencia inclui sempre o tamanho do arquivo e o limite -
        # a desproporcao entre 68 bytes e o limite ja conta a historia.
        evidence: dict[str, Any] = {
            "file_size_bytes": file_size,
            "pixel_limit": MAX_SAFE_PIXELS,
        }

        if image.width is not None and image.height is not None:
            evidence["declared_width"] = image.width
            evidence["declared_height"] = image.height
            evidence["declared_megapixels"] = image.megapixels

        indicators.append(Indicator(rule=DECOMPRESSION_BOMB, evidence=evidence))

    if image.gps is not None:
        indicators.append(
            Indicator(
                rule=GPS_COORDINATES,
                evidence={
                    "latitude": image.gps.latitude,
                    "longitude": image.gps.longitude,
                },
            )
        )

    return indicators


def _email_indicators(email: EmailAnalysis | None) -> list[Indicator]:
    """Indicadores derivados dos cabecalhos e do corpo da mensagem.

    Repare no que NAO vira indicador: ausencia de resultado de autenticacao.
    Um `.eml` exportado antes da entrega, ou salvo de um cliente que nao
    grava esses cabecalhos, simplesmente nao tem o dado - e nao ter nao e o
    mesmo que falhar.
    """
    if email is None:
        return []

    indicators = []
    auth = email.authentication

    if auth.spf_failed:
        indicators.append(Indicator(rule=SPF_FAILED, evidence={"spf": auth.spf}))

    if auth.dkim_failed:
        indicators.append(Indicator(rule=DKIM_FAILED, evidence={"dkim": auth.dkim}))

    if auth.dmarc_failed:
        indicators.append(Indicator(rule=DMARC_FAILED, evidence={"dmarc": auth.dmarc}))

    if email.reply_to_mismatch:
        indicators.append(
            Indicator(
                rule=REPLY_TO_MISMATCH,
                evidence={
                    "from_domain": email.from_domain,
                    "reply_to_domain": email.reply_to_domain,
                },
            )
        )

    if email.return_path_mismatch:
        indicators.append(
            Indicator(
                rule=RETURN_PATH_MISMATCH,
                evidence={
                    "from_domain": email.from_domain,
                    "return_path_domain": email.return_path_domain,
                },
            )
        )

    if misleading := email.misleading_links:
        indicators.append(
            Indicator(
                rule=MISLEADING_LINK,
                evidence={
                    "links": [
                        {"displayed": link.display_text, "destination": link.url}
                        for link in misleading
                    ]
                },
            )
        )

    return indicators


def _attachment_indicators(
    attachment_categories: tuple[tuple[str, FileCategory | None], ...],
) -> list[Indicator]:
    """Indicador de anexo executavel.

    A familia de cada anexo vem da deteccao por magic bytes, nao da extensao -
    entao um `fatura.pdf` cujos bytes comecam com `MZ` e pego aqui.
    """
    executables = [
        filename
        for filename, category in attachment_categories
        if category is FileCategory.EXECUTABLE
    ]

    if not executables:
        return []

    return [
        Indicator(
            rule=EXECUTABLE_ATTACHMENT,
            evidence={"attachments": executables},
        )
    ]


def _truncation_indicators(analysis: FileAnalysis) -> list[Indicator]:
    """Aviso de que a analise nao cobriu o arquivo inteiro.

    Vale zero ponto: um arquivo grande nao e mais perigoso por ser grande. O
    indicador existe para ser honesto sobre o alcance do exame - sem ele, a
    ausencia de achados poderia ser lida como ausencia de conteudo.
    """
    if not analysis.strings.truncated:
        return []

    return [
        Indicator(
            rule=ANALYSIS_TRUNCATED,
            evidence={"strings_extracted": len(analysis.strings.strings)},
        )
    ]
