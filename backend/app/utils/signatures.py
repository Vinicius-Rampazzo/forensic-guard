"""Comparacao dos bytes de uma evidencia com a tabela de assinaturas.

Este modulo e a LOGICA; a tabela de formatos e o DADO, e vive em
`app/constants/signatures.py`.

Tres problemas que o casamento precisa resolver
-----------------------------------------------
1. **Especificidade.** A assinatura de executavel Windows tem dois bytes
   (`MZ`); a de PNG tem oito. Dois bytes casam por acaso com muito mais
   facilidade. Quando mais de um formato casa, vence o que confirmou mais
   bytes - a evidencia mais forte.

2. **Padroes em posicoes diferentes.** WebP, WAV e AVI comecam todos com
   `RIFF`; o que os separa esta no byte 8. Um formato so e reconhecido quando
   TODOS os seus padroes casam.

3. **Formatos sem assinatura.** `.eml` e texto puro, sem magic bytes. A
   deteccao de e-mail e heuristica, por contagem de cabecalhos.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import puremagic

from app.constants.signatures import (
    EMAIL_HEADER_SCAN_SIZE,
    EMAIL_HEADERS,
    MINIMUM_EMAIL_HEADERS,
    SIGNATURE_READ_SIZE,
    SIGNATURES,
    BytePattern,
    FileSignature,
)

# Quantos bytes sao lidos do inicio do arquivo.
#
# Precisa cobrir tanto as assinaturas quanto a varredura de cabecalhos de
# e-mail, para que uma unica leitura sirva aos dois usos.
HEADER_READ_SIZE = max(SIGNATURE_READ_SIZE, EMAIL_HEADER_SCAN_SIZE)


@dataclass(frozen=True)
class SignatureMatch:
    """Um formato que casou com os bytes do arquivo.

    Attributes:
        signature: o formato reconhecido.
        confirmed_bytes: quantos bytes foram efetivamente conferidos. E a
            medida de forca da evidencia: oito bytes conferidos sustentam uma
            conclusao muito melhor que dois.
    """

    signature: FileSignature
    confirmed_bytes: int


def read_header(path: Path) -> bytes:
    """Le apenas o inicio do arquivo, o suficiente para identifica-lo.

    Nao usa `path.read_bytes()`: a evidencia pode ter gigabytes, e para
    reconhecer o formato bastam alguns milhares de bytes do comeco.
    """
    with path.open("rb") as stream:
        return stream.read(HEADER_READ_SIZE)


def pattern_matches(header: bytes, pattern: BytePattern) -> bool:
    """Diz se um padrao de bytes aparece na posicao esperada.

    Arquivo menor que a posicao exigida simplesmente nao casa - nao e erro.
    Um arquivo de 3 bytes nunca sera um WebP, que precisa de pelo menos 12.
    """
    end = pattern.offset + len(pattern.magic)

    if len(header) < end:
        return False

    return header[pattern.offset : end] == pattern.magic


def signature_matches(header: bytes, signature: FileSignature) -> bool:
    """Diz se TODOS os padroes de um formato casam.

    O "todos" e o que separa WebP de WAV: os dois tem `RIFF` no inicio, mas
    apenas um tem `WEBP` no byte 8.
    """
    return all(pattern_matches(header, pattern) for pattern in signature.patterns)


def confirmed_bytes(signature: FileSignature) -> int:
    """Soma os bytes conferidos por todos os padroes do formato."""
    return sum(len(pattern.magic) for pattern in signature.patterns)


def match_signatures(header: bytes) -> list[SignatureMatch]:
    """Devolve todos os formatos que casam, do mais forte para o mais fraco.

    Mais de um resultado nao e defeito: `CA FE BA BE` identifica tanto um
    arquivo .class de Java quanto um binario universal do macOS. Expor a
    ambiguidade e mais honesto que escolher um e esconder o outro.

    O desempate por nome existe para que a ordem seja estavel entre execucoes
    - resultado que muda sozinho e impossivel de testar.
    """
    matches = [
        SignatureMatch(signature=signature, confirmed_bytes=confirmed_bytes(signature))
        for signature in SIGNATURES
        if signature_matches(header, signature)
    ]

    return sorted(matches, key=lambda match: (-match.confirmed_bytes, match.signature.name))


def detect_signature(header: bytes) -> SignatureMatch | None:
    """Devolve o formato mais provavel, ou None quando nada e reconhecido.

    None e um resultado legitimo e comum: arquivos de texto, CSV e JSON nao
    tem assinatura nenhuma. Ausencia de assinatura nao e suspeita.
    """
    matches = match_signatures(header)
    return matches[0] if matches else None


def guess_with_puremagic(header: bytes) -> str | None:
    """Segunda opiniao sobre o tipo MIME, via biblioteca externa.

    Nossa tabela cobre bem os formatos que interessam a uma triagem; o
    puremagic cobre centenas. Ele entra como opiniao complementar, nunca
    substituindo a tabela.

    Devolve None quando nao reconhece. A captura e ampla de proposito: esta
    funcao recebe bytes de origem hostil, e uma excecao inesperada de um
    parser externo nao pode derrubar a analise inteira.
    """
    try:
        return puremagic.from_string(header, mime=True) or None
    except puremagic.PureError:
        return None
    except Exception:  # noqa: BLE001 - parser externo sobre entrada nao confiavel
        return None


def count_email_headers(header: bytes) -> int:
    """Conta quantos cabecalhos distintos de e-mail aparecem no inicio.

    Arquivos .eml nao tem magic bytes: sao texto puro que comeca direto nos
    cabecalhos. A unica forma de reconhece-los e procurar a estrutura definida
    pela RFC 5322.

    Duas precaucoes contra falso positivo:

    - so conta cabecalho no COMECO DA LINHA. Sem isso, um texto que mencione
      "Subject: reuniao" no meio de um paragrafo contaria;
    - conta cabecalhos DISTINTOS. Uma cadeia de e-mail com dez `Received:`
      conta uma vez, e nao dez.
    """
    # errors="ignore" descarta bytes que nao formam texto valido. Cabecalhos de
    # e-mail sao ASCII por definicao, entao o que nao decodifica nao interessa -
    # e um arquivo binario qualquer nao pode derrubar a deteccao.
    text = header.decode("utf-8", errors="ignore").lower()

    found = {
        name
        for line in text.splitlines()
        for name in EMAIL_HEADERS
        if line.startswith(name)
    }

    return len(found)


def looks_like_email(header: bytes) -> bool:
    """Diz se o conteudo tem estrutura de e-mail.

    Repare que a extensao do arquivo nao entra nesta decisao. E deliberado: um
    phishing salvo como `fatura.txt` continua sendo um e-mail, e a extensao e
    justamente o que nao se deve usar como prova.
    """
    return count_email_headers(header) >= MINIMUM_EMAIL_HEADERS
