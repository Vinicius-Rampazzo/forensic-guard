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
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from app.utils.streaming import read_chunks

# Numero de valores possiveis para um byte, e portanto o tamanho da tabela de
# frequencias: 0 a 255.
BYTE_VALUES = 256

# Valor maximo teorico da entropia de um byte, em bits.
MAX_ENTROPY = 8.0

# Em quantos pedacos o arquivo e dividido para o mapa de entropia.
#
# 64 colunas e o equilibrio entre resolucao e legibilidade: o suficiente para
# uma secao empacotada aparecer como um planalto, sem virar ruido visual nem
# inchar a resposta.
DEFAULT_PROFILE_BLOCKS = 64

# Tamanho minimo de um bloco do perfil.
#
# A entropia de 4 bytes nao significa nada - com tao poucas amostras, qualquer
# sequencia parece aleatoria. Abaixo deste tamanho o arquivo recebe menos
# blocos em vez de blocos sem sentido.
MIN_PROFILE_BLOCK_SIZE = 256


@dataclass(frozen=True)
class EntropyProfile:
    """Entropia do arquivo inteiro e de cada pedaco dele.

    Attributes:
        overall: entropia do arquivo completo, de 0 a 8.
        blocks: entropia de cada pedaco, na ordem em que aparecem no arquivo.
            Vazio para arquivo vazio.

    Por que os dois juntos
    ----------------------
    O valor global e a soma das contagens de todos os blocos - entao calcular
    os dois exige uma leitura so. Separa-los em duas funcoes custaria um passe
    inteiro a mais sobre um arquivo que pode ter um gigabyte.

    Por que o mapa importa
    ----------------------
    A entropia global de um executavel empacotado fica em torno de 6,5: a
    media entre o codigo normal e a secao comprimida esconde as duas. O mapa
    mostra o planalto - a regiao onde o valor salta para perto de 8 - que e
    exatamente o que um analista procura.
    """

    overall: float
    blocks: tuple[float, ...]


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


def compute_entropy_profile(
    path: Path,
    block_count: int = DEFAULT_PROFILE_BLOCKS,
) -> EntropyProfile:
    """Calcula a entropia global e a de cada pedaco do arquivo.

    Numa unica leitura: as contagens de bytes de todos os blocos somadas dao
    exatamente a contagem do arquivo inteiro, entao o valor global sai de
    graca junto com o mapa.

    Args:
        path: caminho do arquivo.
        block_count: em quantos pedacos dividir. O numero real pode ser menor
            quando o arquivo e pequeno demais para blocos significativos.

    Returns:
        O perfil. Arquivo vazio devolve entropia 0 e nenhum bloco.
    """
    size = path.stat().st_size

    if size == 0:
        return EntropyProfile(overall=0.0, blocks=())

    # Arquivos pequenos recebem menos blocos, nunca blocos minusculos: a
    # entropia de poucos bytes e um numero sem significado.
    usable_blocks = max(1, min(block_count, size // MIN_PROFILE_BLOCK_SIZE))
    block_size = max(MIN_PROFILE_BLOCK_SIZE, -(-size // usable_blocks))

    total_counts: Counter[int] = Counter()
    block_entropies: list[float] = []

    with path.open("rb") as stream:
        current: Counter[int] = Counter()
        bytes_in_block = 0

        for chunk in read_chunks(stream):
            # Um bloco do perfil pode ser maior ou menor que um bloco de
            # leitura, entao o chunk e consumido em fatias ate acabar.
            position = 0

            while position < len(chunk):
                remaining = block_size - bytes_in_block
                slice_ = chunk[position : position + remaining]

                current.update(slice_)
                total_counts.update(slice_)

                bytes_in_block += len(slice_)
                position += len(slice_)

                if bytes_in_block >= block_size:
                    block_entropies.append(entropy_from_counts(current))
                    current = Counter()
                    bytes_in_block = 0

        # O ultimo bloco costuma ficar incompleto; ele conta do mesmo jeito.
        if bytes_in_block > 0:
            block_entropies.append(entropy_from_counts(current))

    return EntropyProfile(
        overall=entropy_from_counts(total_counts),
        blocks=tuple(block_entropies),
    )


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
