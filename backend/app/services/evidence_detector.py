"""Identificacao do tipo de evidencia e deteccao de contradicoes.

Responsabilidade
----------------
Este servico responde a duas perguntas:

1. **O que e esta evidencia?** Arquivo generico, imagem ou e-mail - o que
   decide qual analisador especifico sera executado depois.
2. **O que ela DIZ que e bate com o que ela E?** A comparacao entre a extensao
   declarada e a assinatura real.

Ele reporta FATOS, nao vereditos. Nao atribui pontuacao nem severidade: isso e
trabalho do Risk Engine. A divisao importa porque os pesos do risco mudam com
o tempo, e a deteccao nao deveria mudar junto.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path, PureWindowsPath

from app.constants.signatures import FileCategory
from app.utils.signatures import (
    SignatureMatch,
    guess_with_puremagic,
    looks_like_email,
    match_signatures,
    read_header,
)


class EvidenceType(StrEnum):
    """Famílias de evidencia que o ForensicGuard trata de forma distinta."""

    FILE = "file"
    IMAGE = "image"
    EMAIL = "email"


class MismatchKind(StrEnum):
    """Tipo de contradicao entre o nome declarado e o conteudo real."""

    NONE = "none"
    """Sem contradicao, ou sem base para afirmar que exista."""

    TYPE_MISMATCH = "type_mismatch"
    """A extensao nao corresponde ao formato detectado."""

    EXECUTABLE_DISGUISED = "executable_disguised"
    """O conteudo e executavel e a extensao sugere outra coisa.

    O caso mais grave que esta etapa consegue reconhecer: `invoice.jpg` cujos
    bytes comecam com `MZ`.
    """


@dataclass(frozen=True)
class EvidenceDetection:
    """O que se descobriu sobre a identidade da evidencia.

    Attributes:
        evidence_type: familia usada para escolher o analisador seguinte.
        declared_extension: extensao extraida do nome informado pelo usuario,
            em minusculas e com o ponto. Vazia quando nao ha extensao.
        detected_name: nome legivel do formato reconhecido.
        detected_mime: MIME do formato reconhecido.
        detected_category: familia do formato reconhecido.
        confirmed_bytes: quantos bytes sustentam a conclusao. Dois bytes
            (como `MZ` ou `BM`) sao evidencia fraca; oito, forte. O Risk
            Engine usa isso para calibrar a confianca.
        ambiguous_with: outros formatos que tambem casaram. Quase sempre
            vazio; nao vazio significa que os bytes sao genuinamente
            ambiguos, como `CA FE BA BE`.
        puremagic_mime: segunda opiniao de uma biblioteca independente.
        second_opinion_agrees: None quando uma das duas nao opinou.
        mismatch: o tipo de contradicao encontrada.
        notes: observacoes do formato reconhecido, exibidas no relatorio.
    """

    evidence_type: EvidenceType
    declared_extension: str
    detected_name: str | None
    detected_mime: str | None
    detected_category: FileCategory | None
    confirmed_bytes: int
    ambiguous_with: tuple[str, ...]
    puremagic_mime: str | None
    second_opinion_agrees: bool | None
    mismatch: MismatchKind
    notes: tuple[str, ...]


def extract_extension(filename: str) -> str:
    """Extrai a extensao de um nome de arquivo nao confiavel.

    O nome vem do usuario e pode conter qualquer coisa - inclusive separadores
    de caminho, numa tentativa de path traversal. Aqui ele NUNCA e usado para
    abrir nada: so se le a extensao.

    Usa PureWindowsPath porque ela reconhece tanto `/` quanto `\\` como
    separador, em qualquer sistema operacional. PurePosixPath ignoraria a barra
    invertida, e `..\\..\\evil.exe` devolveria uma extensao errada no Linux.

    A classe Pure* nunca toca no disco: ela so manipula o texto do caminho.
    """
    return PureWindowsPath(filename).suffix.lower()


def classify_evidence_type(
    header: bytes,
    match: SignatureMatch | None,
) -> EvidenceType:
    """Decide qual analisador especifico a evidencia deve percorrer.

    A checagem de e-mail vem primeiro porque `.eml` nao tem assinatura: se
    dependesse dos magic bytes, nunca seria reconhecido.
    """
    if looks_like_email(header):
        return EvidenceType.EMAIL

    if match is not None and match.signature.category is FileCategory.IMAGE:
        return EvidenceType.IMAGE

    return EvidenceType.FILE


def classify_mismatch(declared_extension: str, match: SignatureMatch | None) -> MismatchKind:
    """Compara o que o arquivo diz ser com o que ele e.

    A parte dificil nao e achar diferenca - e nao gritar a toa. Tres situacoes
    parecem mismatch e nao sao:

    - **Extensao alternativa.** `.jpeg` e `.jpg` sao o mesmo formato. Por isso
      cada assinatura carrega uma lista de extensoes legitimas.
    - **Formato contaminer.** Um `.docx` E um ZIP por dentro; detectar "ZIP"
      ali esta correto. Dai o campo `container_extensions`.
    - **Formato desconhecido.** Quando nada foi reconhecido, nao ha base para
      afirmar contradicao. Arquivos de texto, CSV e JSON nao tem assinatura, e
      ausencia de assinatura nunca e suspeita.

    Limitacao conhecida: assinaturas curtas geram falso positivo. `BM`, de
    bitmap, tem dois bytes e casa por acaso com alguma frequencia. Por isso o
    resultado carrega `confirmed_bytes` - cabe ao Risk Engine pesar uma
    conclusao sustentada por dois bytes de forma diferente de uma sustentada
    por oito.
    """
    if match is None:
        return MismatchKind.NONE

    # Sem extensao nao ha afirmacao a ser contradita. Comum em executaveis
    # Linux e em anexos sem nome.
    if not declared_extension:
        return MismatchKind.NONE

    signature = match.signature

    if declared_extension in signature.extensions:
        return MismatchKind.NONE

    if declared_extension in signature.container_extensions:
        return MismatchKind.NONE

    # A partir daqui ha contradicao real. Resta saber a gravidade.
    #
    # Conteudo executavel sob extensao de outra coisa e a situacao classica de
    # entrega de malware: o usuario acredita abrir uma fatura e executa um
    # programa. Qualquer outra divergencia pode ser apenas um arquivo mal
    # nomeado.
    if signature.category is FileCategory.EXECUTABLE:
        return MismatchKind.EXECUTABLE_DISGUISED

    return MismatchKind.TYPE_MISMATCH


def compare_opinions(detected_mime: str | None, puremagic_mime: str | None) -> bool | None:
    """Confronta a tabela propria com a biblioteca externa.

    Devolve None quando uma das duas nao opinou - ausencia de opiniao nao e
    discordancia.

    Divergencia entre dois metodos independentes e informacao util num
    relatorio forense, e nao ruido a ser escondido. Quem le decide o que fazer
    com ela.
    """
    if detected_mime is None or puremagic_mime is None:
        return None

    return detected_mime == puremagic_mime


def detect_evidence(path: Path, original_filename: str | None = None) -> EvidenceDetection:
    """Identifica a evidencia e verifica se o nome dela condiz com o conteudo.

    Args:
        path: caminho do arquivo em disco. Nas etapas seguintes sera um
            temporario com nome gerado internamente.
        original_filename: nome informado pelo usuario no upload. Precisa ser
            separado de `path` justamente porque o arquivo e gravado com um
            nome interno seguro - a extensao a ser auditada e a do nome
            original, nao a do temporario. Quando omitido, usa o nome do
            proprio caminho.

    Returns:
        O que foi descoberto. Nenhum campo e um veredito: sao observacoes.
    """
    header = read_header(path)

    # match_signatures ja devolve a lista ordenada do mais forte para o mais
    # fraco, entao o primeiro elemento e a melhor conclusao disponivel.
    matches = match_signatures(header)
    best = matches[0] if matches else None

    declared_extension = extract_extension(original_filename or path.name)
    detected_mime = best.signature.mime if best else None
    puremagic_mime = guess_with_puremagic(header)

    notes = tuple(match.signature.note for match in matches if match.signature.note)

    return EvidenceDetection(
        evidence_type=classify_evidence_type(header, best),
        declared_extension=declared_extension,
        detected_name=best.signature.name if best else None,
        detected_mime=detected_mime,
        detected_category=best.signature.category if best else None,
        confirmed_bytes=best.confirmed_bytes if best else 0,
        # O primeiro resultado e o escolhido; os demais sao a ambiguidade.
        ambiguous_with=tuple(match.signature.name for match in matches[1:]),
        puremagic_mime=puremagic_mime,
        second_opinion_agrees=compare_opinions(detected_mime, puremagic_mime),
        mismatch=classify_mismatch(declared_extension, best),
        notes=notes,
    )
