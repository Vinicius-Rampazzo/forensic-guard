"""Dados para a analise heuristica de URLs.

Este modulo e DADO, nao logica. A comparacao vive em
`app/analyzers/url_analyzer.py`.

Um aviso que vale para o arquivo inteiro: **nada aqui identifica algo como
malicioso.** Sao caracteristicas incomuns. Um encurtador e um servico
legitimo; um dominio `.xyz` pode ser de uma empresa seria; HTTP sem TLS
existe em rede interna o tempo todo. O valor esta na combinacao, nunca no
item isolado.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Esquemas
# ---------------------------------------------------------------------------

# Esquemas que executam codigo ou embutem conteudo em vez de apontar para um
# endereco. Numa mensagem de e-mail eles quase nunca tem uso legitimo.
#
# `data:` merece destaque: ele carrega a pagina inteira dentro da propria URL,
# entao um formulario de phishing pode viver sem servidor nenhum - e sem
# dominio para ser denunciado ou derrubado.
DANGEROUS_SCHEMES = frozenset({"javascript", "data", "vbscript", "file", "blob"})

# Porta padrao de cada esquema. Uma porta diferente nao e problema por si -
# mas infraestrutura improvisada costuma usar portas altas, enquanto servico
# legitimo voltado ao publico quase sempre usa a padrao.
STANDARD_PORTS = {
    "http": 80,
    "https": 443,
    "ftp": 21,
    "ftps": 990,
}


# ---------------------------------------------------------------------------
# Dominios de topo
# ---------------------------------------------------------------------------

# TLDs com taxa de abuso desproporcional.
#
# Dois grupos:
#
# 1. **Gratuitos ou quase.** Os do antigo Freenom (.tk, .ml, .ga, .cf, .gq)
#    eram registraveis sem custo e sem verificacao, o que os tornou o endereco
#    padrao de campanhas descartaveis.
#
# 2. **Colisao com extensao de arquivo.** `.zip` e `.mov` foram liberados em
#    2023 e sao exatamente iguais a extensoes conhecidas. Isso permite que um
#    texto como "baixe o relatorio.zip" vire um link clicavel para um dominio
#    controlado pelo atacante, sem que ninguem tenha escrito uma URL.
RISKY_TLDS = frozenset(
    {
        # gratuitos / sem verificacao
        "tk",
        "ml",
        "ga",
        "cf",
        "gq",
        # colidem com extensao de arquivo
        "zip",
        "mov",
        # historicamente associados a campanhas de baixo custo
        "top",
        "xyz",
        "click",
        "link",
        "work",
        "country",
        "stream",
        "download",
        "loan",
        "review",
        "cam",
        "rest",
        "quest",
        "cfd",
        "sbs",
        "icu",
        "bar",
        "monster",
        "lol",
        "buzz",
    }
)

# Sufixos de duas partes comuns, usados para contar subdominios corretamente.
#
# Sem esta lista, `empresa.com.br` pareceria ter um subdominio a mais que
# `empresa.com`, e todo site brasileiro legitimo seria marcado.
#
# E uma aproximacao deliberada: a lista completa de sufixos publicos tem
# milhares de entradas e muda com frequencia. Estes cobrem a grande maioria do
# trafego que esta ferramenta vai ver.
MULTIPART_SUFFIXES = frozenset(
    {
        "com.br",
        "net.br",
        "org.br",
        "gov.br",
        "edu.br",
        "com.ar",
        "com.mx",
        "co.uk",
        "org.uk",
        "ac.uk",
        "gov.uk",
        "co.jp",
        "co.kr",
        "co.in",
        "com.au",
        "net.au",
        "org.au",
        "co.za",
        "com.cn",
        "com.tr",
        "com.pt",
    }
)

# Acima deste numero de rotulos antes do dominio registravel, a URL e
# considerada ofuscada por subdominios.
#
# A tecnica: `banco.com.br.seguranca-conta.exemplo.com` tem o nome do banco
# no inicio, que e onde o olho para ao ler rapido - mas o dominio de verdade
# e `exemplo.com`.
MAX_SUBDOMAIN_LABELS = 3


# ---------------------------------------------------------------------------
# Encurtadores
# ---------------------------------------------------------------------------

# Servicos de encurtamento conhecidos.
#
# Encurtador nao e malicioso - e um servico comum e util. O que ele faz, do
# ponto de vista da analise, e **esconder o destino**: nao da para avaliar
# para onde a URL aponta sem acessa-la, e acessar e justamente o que uma
# triagem offline nao faz.
URL_SHORTENERS = frozenset(
    {
        "bit.ly",
        "tinyurl.com",
        "goo.gl",
        "t.co",
        "ow.ly",
        "is.gd",
        "buff.ly",
        "rebrand.ly",
        "cutt.ly",
        "shorturl.at",
        "rb.gy",
        "tiny.cc",
        "bl.ink",
        "s.id",
        "v.gd",
        "clck.ru",
        "u.to",
        "adf.ly",
        "bc.vc",
        "j.mp",
        "lnkd.in",
        "db.tt",
        "qr.net",
        "ity.im",
        "q.gs",
        "po.st",
        "tr.im",
        "x.co",
        "short.io",
        "encurtador.com.br",
        "bit.do",
        "soo.gd",
        "1url.com",
    }
)


# Formato tipico de um redirecionador, para alcancar os que nao estao na lista.
#
# A lista acima tem um limite estrutural: ela so pega o que alguem ja pensou em
# listar. Existem centenas de servicos de encurtamento, e qualquer pessoa pode
# hospedar o proprio em dez minutos - entao a lista esta permanentemente
# desatualizada, por construcao.
#
# A saida e parar de perguntar "este dominio e conhecido?" e passar a perguntar
# "esta URL tem a forma de um redirecionador?". A forma e bem caracteristica:
#
#     https://linkly.link/2zAps
#            |___________|_____|
#              host curto   um unico segmento curto e aleatorio
#
# Tres sinais juntos:
#   1. host curto, sem subdominio (o servico vende brevidade);
#   2. caminho com UM segmento so, curto, sem extensao nem palavra legivel;
#   3. nada de parametros nem fragmento - o identificador E o caminho.
#
# Isoladamente cada um aparece em URLs comuns. Os tres ao mesmo tempo, nao:
# um site de verdade quase sempre tem caminho descritivo, mais de um nivel,
# ou parametros.

# Acima disto o dominio e longo demais para um servico que vende brevidade.
MAX_SHORTENER_HOST_LENGTH = 15

# Comprimento maximo do identificador. Encurtadores usam de 4 a 10 caracteres;
# acima disso costuma ser caminho de verdade.
MAX_SHORTENER_PATH_LENGTH = 12

# Abaixo disto nao da para distinguir identificador de palavra curta.
MIN_SHORTENER_PATH_LENGTH = 4


# ---------------------------------------------------------------------------
# Caminho
# ---------------------------------------------------------------------------

# Extensoes que executam ao serem abertas, ou que levam a isso.
#
# Uma URL que termina em `.exe` nao e necessariamente maliciosa - sites de
# software distribuem instaladores assim. Mas num link recebido por e-mail,
# costuma ser o passo final da entrega.
EXECUTABLE_PATH_EXTENSIONS = frozenset(
    {
        ".exe",
        ".scr",
        ".bat",
        ".cmd",
        ".com",
        ".pif",
        ".vbs",
        ".vbe",
        ".js",
        ".jse",
        ".wsf",
        ".wsh",
        ".jar",
        ".msi",
        ".ps1",
        ".hta",
        ".lnk",
        ".reg",
        ".apk",
        ".dmg",
        ".iso",
        ".img",
        ".cpl",
    }
)

# Extensoes que o usuario espera que sejam inofensivas. A presenca de uma
# delas ANTES de uma extensao executavel e a assinatura do disfarce:
# `fatura.pdf.exe` aparece como "fatura.pdf" em sistemas que escondem a
# extensao final.
DECOY_EXTENSIONS = frozenset(
    {
        ".pdf",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".ppt",
        ".pptx",
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".txt",
        ".csv",
        ".zip",
        ".rar",
    }
)


# ---------------------------------------------------------------------------
# Ofuscacao
# ---------------------------------------------------------------------------

# A partir deste comprimento, a URL e considerada longa demais.
#
# Importa porque a barra de endereco tem largura limitada: numa URL muito
# longa, o dominio real some do campo visivel e o usuario le apenas o comeco -
# que o atacante controla.
MAX_URL_LENGTH = 150

# Quantidade de sequencias `%XX` a partir da qual a URL e considerada
# ofuscada. Codificacao percentual e normal em parametros com acentuacao ou
# espaco; em excesso, costuma servir para esconder o que esta escrito.
MAX_PERCENT_ENCODINGS = 8
