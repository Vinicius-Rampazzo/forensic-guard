"""Extracao de strings legiveis e de artefatos de uma evidencia.

O que este modulo faz
---------------------
Todo arquivo binario carrega trechos de texto legivel: nomes de funcoes, URLs,
caminhos, mensagens de erro, chaves de registro. O comando `strings` do Linux
existe ha decadas exatamente para isso, e este modulo e o equivalente dele em
Python, com um passo a mais: alem de extrair o texto, ele procura padroes que
interessam a uma triagem forense.

Duas tecnicas de extracao
-------------------------
1. **ASCII**: sequencias de bytes imprimiveis (0x20 a 0x7E).
2. **UTF-16LE**: o mesmo, mas com um byte nulo entre cada caractere. Executaveis
   do Windows guardam a maioria das strings nesse formato, entao ignora-lo
   deixaria de fora justamente o que mais interessa num PE.

Limites de seguranca
--------------------
A aplicacao processa arquivos nao confiaveis. Todo laco que cresce junto com a
entrada precisa de teto, ou vira negacao de servico: um arquivo de 2 GB geraria
milhoes de strings e esgotaria a memoria. Por isso existem MAX_SCAN_BYTES e
MAX_STRINGS, e o resultado informa quando houve corte.

O que este modulo NAO faz
-------------------------
Nao conclui nada. Encontrar "powershell.exe" dentro de um arquivo nao significa
que ele seja malicioso - instaladores legitimos e ferramentas de administracao
tambem contem essa string. O que ele produz sao **artefatos**, materia-prima
para o Risk Engine.
"""

from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass, field
from pathlib import Path

# Tamanho minimo de uma sequencia para ser considerada uma string.
#
# Quatro e o mesmo padrao do comando `strings` do Linux, e o motivo e
# estatistico: em dados binarios aleatorios, sequencias de 1 a 3 bytes
# imprimiveis aparecem o tempo todo por acaso. A partir de 4, a chance de
# coincidencia cai o suficiente para que a sequencia provavelmente seja texto
# de verdade.
MIN_STRING_LENGTH = 4

# Quantidade maxima de bytes lidos do arquivo (8 MiB).
# Strings relevantes tendem a aparecer no inicio; ler o arquivo inteiro nao
# compensa o custo em memoria e tempo.
MAX_SCAN_BYTES = 8 * 1024 * 1024

# Quantidade maxima de strings devolvidas.
MAX_STRINGS = 5_000

# Quantidade maxima de artefatos por categoria.
MAX_ARTIFACTS_PER_CATEGORY = 200


# ---------------------------------------------------------------------------
# Padroes de artefatos
#
# Compilados uma unica vez, na importacao do modulo. Compilar dentro de uma
# funcao chamada em laco refaria o mesmo trabalho a cada iteracao.
# ---------------------------------------------------------------------------

URL_PATTERN = re.compile(r"\b(?:https?|ftp)://[^\s\"'<>()\[\]{}]{4,}", re.IGNORECASE)

# Candidatos a IPv4. A validacao real fica por conta do modulo ipaddress:
# regex e bom em reconhecer formato, mas ruim em validar semantica. Escrever um
# padrao que rejeite 999.999.999.999 e possivel, porem ilegivel.
IPV4_CANDIDATE_PATTERN = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")

# Candidatos a IPv6: pelo menos dois grupos separados por dois-pontos.
# Tambem validados depois pelo modulo ipaddress.
IPV6_CANDIDATE_PATTERN = re.compile(r"\b[0-9A-Fa-f]{0,4}(?::[0-9A-Fa-f]{0,4}){2,7}\b")

EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")

# Caminhos absolutos do Windows: letra de unidade, dois-pontos, barra invertida.
# A classe negada exclui os caracteres que o proprio Windows proibe em nomes.
WINDOWS_PATH_PATTERN = re.compile(r"\b[A-Za-z]:\\[^\s\"'<>|*?\r\n]{2,}")

# Binarios do proprio Windows frequentemente usados para executar codigo sem
# instalar nada. A tecnica se chama "Living Off the Land", e essas ferramentas
# sao conhecidas como LOLBins.
#
# Presenca nao e culpa: instaladores e scripts de administracao legitimos usam
# as mesmas ferramentas. O valor esta na combinacao com outros indicadores.
SUSPICIOUS_KEYWORDS = (
    # interpretadores e utilitarios abusaveis
    "powershell.exe",
    "cmd.exe",
    "wscript.exe",
    "cscript.exe",
    "mshta.exe",
    "rundll32.exe",
    "regsvr32.exe",
    "certutil.exe",
    "bitsadmin.exe",
    "schtasks.exe",
    "vssadmin.exe",
    "wmic.exe",
    # tecnicas comuns de execucao e ofuscacao
    "-encodedcommand",
    "-windowstyle hidden",
    "-noprofile",
    "invoke-expression",
    "invoke-webrequest",
    "downloadstring",
    "downloadfile",
    "frombase64string",
    "iex(",
)


@dataclass
class StringAnalysis:
    """Resultado da analise de strings de uma evidencia.

    Attributes:
        strings: sequencias legiveis encontradas, sem repeticao.
        artifacts: artefatos por categoria (urls, ipv4, emails, ...).
        truncated: True se algum limite de seguranca cortou o resultado, o que
            significa que a analise e parcial. Informar isso e importante: um
            relatorio forense nao pode dar a entender que examinou tudo quando
            examinou parte.
    """

    strings: list[str] = field(default_factory=list)
    artifacts: dict[str, list[str]] = field(default_factory=dict)
    truncated: bool = False


# ---------------------------------------------------------------------------
# Extracao de strings
# ---------------------------------------------------------------------------


def extract_ascii_strings(data: bytes, min_length: int = MIN_STRING_LENGTH) -> list[str]:
    """Extrai sequencias de bytes imprimiveis ASCII.

    A faixa 0x20 a 0x7E cobre do espaco ao til: letras, digitos, pontuacao e
    simbolos. Fora dela ficam os caracteres de controle, que quebram a
    sequencia.
    """
    pattern = re.compile(rb"[\x20-\x7e]{%d,}" % min_length)
    return [match.decode("ascii") for match in pattern.findall(data)]


def extract_utf16_strings(data: bytes, min_length: int = MIN_STRING_LENGTH) -> list[str]:
    """Extrai sequencias UTF-16LE de caracteres ASCII.

    Em UTF-16LE, o caractere "A" e gravado como 41 00: o byte do caractere
    seguido de um byte nulo. O padrao abaixo procura essa alternancia.

    Duas limitacoes conhecidas e aceitas:

    1. Cobre apenas caracteres da faixa ASCII, que e o caso dominante em
       binarios do Windows. Texto UTF-16 com acentuacao ou alfabetos nao
       latinos nao e capturado.
    2. Quando texto ASCII e seguido de um byte nulo, o ultimo caractere dele
       mais esse nulo ja formam um par valido, e o casamento absorve esse
       caractere - "...Guard\\x00" + "payload" em UTF-16 produz "dpayload".
       Arquivos binarios nao garantem alinhamento, entao nao ha forma
       confiavel de saber onde uma sequencia UTF-16 comeca. O `strings -el` do
       Linux tem o mesmo comportamento. O impacto e baixo porque a extracao de
       artefatos usa fronteira de palavra e prefixos de protocolo.
    """
    pattern = re.compile(rb"(?:[\x20-\x7e]\x00){%d,}" % min_length)
    return [match.decode("utf-16-le") for match in pattern.findall(data)]


def extract_strings(data: bytes, min_length: int = MIN_STRING_LENGTH) -> list[str]:
    """Extrai strings ASCII e UTF-16LE, sem repeticao e preservando a ordem."""
    ascii_strings = extract_ascii_strings(data, min_length)
    utf16_strings = extract_utf16_strings(data, min_length)
    return _unique(ascii_strings + utf16_strings)


# ---------------------------------------------------------------------------
# Extracao de artefatos
# ---------------------------------------------------------------------------


def extract_artifacts(strings: list[str]) -> dict[str, list[str]]:
    """Procura padroes de interesse forense nas strings extraidas.

    Returns:
        Dicionario de categoria para lista de artefatos. Categorias sem nenhuma
        ocorrencia sao omitidas, para que o relatorio nao fique cheio de listas
        vazias.
    """
    haystack = "\n".join(strings)

    found = {
        "urls": _unique(URL_PATTERN.findall(haystack)),
        "ipv4": _unique(_valid_ip_addresses(IPV4_CANDIDATE_PATTERN.findall(haystack), version=4)),
        "ipv6": _unique(_valid_ip_addresses(IPV6_CANDIDATE_PATTERN.findall(haystack), version=6)),
        "emails": _unique(EMAIL_PATTERN.findall(haystack)),
        "windows_paths": _unique(WINDOWS_PATH_PATTERN.findall(haystack)),
        "suspicious_keywords": _find_suspicious_keywords(haystack),
    }

    return {
        category: values[:MAX_ARTIFACTS_PER_CATEGORY]
        for category, values in found.items()
        if values
    }


def _valid_ip_addresses(candidates: list[str], version: int) -> list[str]:
    """Filtra candidatos, mantendo apenas enderecos IP realmente validos.

    Aqui esta a divisao de trabalho: o regex encontrou qualquer coisa com forma
    de IP, e o modulo ipaddress - biblioteca padrao, escrita e testada por
    terceiros - decide o que e valido de verdade. "999.999.999.999" tem forma
    de IPv4 mas nao e um.

    Falso positivo conhecido e aceito: numeros de versao como "1.2.3.4" sao
    enderecos IPv4 validos e serao capturados. Nenhuma tecnica de extracao
    estatica distingue os dois casos sem contexto, e ocultar o artefato seria
    pior que exibi-lo - quem le o relatorio consegue julgar.
    """
    valid = []

    for candidate in candidates:
        try:
            address = ipaddress.ip_address(candidate)
        except ValueError:
            continue

        if address.version == version:
            valid.append(candidate)

    return valid


def _find_suspicious_keywords(haystack: str) -> list[str]:
    """Devolve as palavras-chave suspeitas presentes no texto.

    A comparacao ignora maiusculas e minusculas porque o Windows nao as
    distingue em nomes de arquivo, e ofuscacao simples costuma alternar a caixa
    das letras justamente para escapar de buscas ingenuas.
    """
    lowered = haystack.lower()
    return [keyword for keyword in SUSPICIOUS_KEYWORDS if keyword in lowered]


# ---------------------------------------------------------------------------
# Entrada principal
# ---------------------------------------------------------------------------


def analyze_strings(path: Path, min_length: int = MIN_STRING_LENGTH) -> StringAnalysis:
    """Analisa as strings de um arquivo.

    Le no maximo MAX_SCAN_BYTES do inicio do arquivo e devolve as strings
    encontradas e os artefatos reconhecidos.
    """
    with path.open("rb") as stream:
        # Le um byte a mais que o limite apenas para descobrir se havia mais
        # conteudo depois dele - sem isso, um arquivo de exatamente 8 MiB seria
        # reportado como truncado.
        data = stream.read(MAX_SCAN_BYTES + 1)

    truncated = len(data) > MAX_SCAN_BYTES
    data = data[:MAX_SCAN_BYTES]

    strings = extract_strings(data, min_length)
    if len(strings) > MAX_STRINGS:
        strings = strings[:MAX_STRINGS]
        truncated = True

    return StringAnalysis(
        strings=strings,
        artifacts=extract_artifacts(strings),
        truncated=truncated,
    )


def _unique(values: list[str]) -> list[str]:
    """Remove repeticoes preservando a ordem de aparecimento.

    dict.fromkeys funciona porque dicionarios do Python mantem a ordem de
    insercao desde a versao 3.7, e chaves nao se repetem. E mais rapido e mais
    curto que montar um set auxiliar a mao.
    """
    return list(dict.fromkeys(values))
