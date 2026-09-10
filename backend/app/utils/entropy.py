"""Calculo da entropia de Shannon de uma evidencia.

O que a entropia mede
---------------------
Ela responde a uma pergunta: **quao imprevisivel e o proximo byte?**

Num texto em portugues, apostar em espaco ou na letra "a" acerta com frequencia
- ha muita estrutura e repeticao. Num arquivo criptografado, nenhuma aposta e
melhor que outra: os bytes parecem sorteados. A entropia poe um numero nessa
diferenca.

A escala vai de 0 a 8 porque um byte tem 8 bits: o valor representa quantos
bits de informacao cada byte realmente carrega, em media.

    0.0    um unico valor de byte repetido (arquivo de zeros)
    ~4.5   texto natural
    ~6.0   executavel comum
    >7.5   comprimido, criptografado ou empacotado (packed)
    8.0    os 256 valores igualmente distribuidos

Por que isso NAO prova nada sozinho
-----------------------------------
Um .zip legitimo, um .jpg, um instalador e um malware empacotado tem entropias
parecidissimas - todos passam de 7.5. A causa e a mesma (compressao), a
intencao e que difere, e a entropia nao enxerga intencao.

Por isso, no ForensicGuard, entropia alta e apenas um **indicador** que soma
alguns pontos ao Risk Score, e nunca uma conclusao. Ela ganha significado
quando combinada com outros sinais - por exemplo, entropia alta num arquivo que
se declara .txt.
"""

from __future__ import annotations

import math
from collections import Counter
from pathlib import Path
from typing import BinaryIO

from app.utils.streaming import read_chunks

# Numero de valores possiveis para um byte, e portanto o tamanho da tabela de
# frequencias: 0 a 255.
BYTE_VALUES = 256

# Valor maximo teorico da entropia de um byte, em bits.
MAX_ENTROPY = 8.0


def compute_entropy(path: Path) -> float:
    """Calcula a entropia de Shannon de um arquivo, em bits por byte.

    Returns:
        Valor entre 0.0 e 8.0. Um arquivo vazio devolve 0.0.
    """
    with path.open("rb") as stream:
        return compute_entropy_from_stream(stream)


def compute_entropy_from_stream(stream: BinaryIO) -> float:
    """Calcula a entropia de um fluxo binario ja aberto."""
    counts = count_byte_frequencies(stream)
    return entropy_from_counts(counts)


def count_byte_frequencies(stream: BinaryIO) -> Counter[int]:
    """Conta quantas vezes cada valor de byte aparece no fluxo.

    Le em blocos pelo mesmo motivo do modulo de hashing: o consumo de memoria
    precisa ser constante, independentemente do tamanho do arquivo. Repare que
    a tabela de frequencias tem no maximo 256 entradas - ela nunca cresce, por
    maior que seja a evidencia.
    """
    counts: Counter[int] = Counter()

    for chunk in read_chunks(stream):
        # Iterar sobre um objeto bytes produz inteiros de 0 a 255, entao o
        # Counter ja recebe exatamente os valores que queremos contar.
        counts.update(chunk)

    return counts


def entropy_from_counts(counts: Counter[int]) -> float:
    """Aplica a formula de Shannon sobre uma tabela de frequencias.

    A formula e:

        H = - SOMA( p_i * log2(p_i) )

    onde p_i e a probabilidade do byte i, ou seja, quantas vezes ele apareceu
    dividido pelo total. O log2 e o que faz o resultado sair em bits, e o sinal
    negativo compensa o fato de o log de um numero entre 0 e 1 ser negativo.

    Intuicao do termo p * log2(p): um byte que aparece sempre (p = 1) contribui
    com zero, porque nao ha surpresa nenhuma nele. Um byte raro carrega muita
    informacao quando aparece, mas aparece pouco - e o produto equilibra os
    dois efeitos.
    """
    total = sum(counts.values())

    # Arquivo vazio: nao ha byte nenhum, logo nao ha imprevisibilidade.
    # Tratado explicitamente porque a formula dividiria por zero.
    if total == 0:
        return 0.0

    entropy = 0.0
    for count in counts.values():
        # Bytes com contagem zero nao entram no somatorio: log2(0) e indefinido
        # e, matematicamente, o limite da contribuicao deles e zero. O Counter
        # so guarda o que apareceu, entao isso ja vem de graca.
        probability = count / total
        entropy -= probability * math.log2(probability)

    return entropy
