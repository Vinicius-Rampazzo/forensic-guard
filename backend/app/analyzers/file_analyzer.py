"""Analise generica, aplicada a toda evidencia independente do formato.

Este e o analisador de base: qualquer arquivo enviado ao ForensicGuard passa
por ele. Analisadores especificos - imagem, e-mail - rodam DEPOIS e em cima
deste resultado, nunca no lugar dele.

Responsabilidade
----------------
Reunir os fatos que valem para qualquer sequencia de bytes:

    tamanho  ->  hashes  ->  entropia  ->  strings e artefatos

Nenhuma conclusao, nenhuma pontuacao. Identificacao de formato tambem nao e
daqui: ela mora em `services/evidence_detector.py`, porque a camada de
analisadores nao pode depender da camada de servicos.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.analyzers.string_analyzer import StringAnalysis, analyze_strings
from app.utils.entropy import compute_entropy
from app.utils.hashing import compute_hashes


@dataclass(frozen=True)
class FileAnalysis:
    """Fatos observados sobre um arquivo qualquer.

    Attributes:
        size: tamanho em bytes.
        hashes: do nome do algoritmo para o valor hexadecimal.
        entropy: entropia de Shannon, de 0 a 8.
        strings: strings legiveis e artefatos reconhecidos.
    """

    size: int
    hashes: dict[str, str]
    entropy: float
    strings: StringAnalysis


def analyze_file(path: Path) -> FileAnalysis:
    """Executa a analise generica de um arquivo.

    Cada etapa le o arquivo por conta propria, em blocos. Sao tres leituras em
    vez de uma, e isso e deliberado: o sistema operacional mantem em cache um
    arquivo recem-lido, entao o custo real e baixo, e cada funcao continua
    independente e testavel sozinha.

    Args:
        path: caminho do arquivo em disco - um temporario, na pratica.

    Returns:
        Os fatos observados. Nenhum deles e veredito.
    """
    return FileAnalysis(
        size=path.stat().st_size,
        hashes=compute_hashes(path),
        entropy=compute_entropy(path),
        strings=analyze_strings(path),
    )
