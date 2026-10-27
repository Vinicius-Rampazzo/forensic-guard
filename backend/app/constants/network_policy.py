"""Politica da unica parte do sistema que fala com a rede.

Resolver um redirecionamento significa pedir a um endereco controlado por
quem esta sendo investigado que o servidor faca uma requisicao. Isso e a
definicao de SSRF - *Server-Side Request Forgery* - e e a superficie de ataque
mais perigosa que esta aplicacao tem.

O ataque e simples: a pessoa envia `https://inocente.com/x`, o servidor pede a
pagina, e ela responde com um redirecionamento para `http://169.254.169.254/`.
Esse endereco, em quase toda nuvem, devolve as credenciais da propria
maquina. Seguir o redirecionamento sem olhar transforma a ferramenta de
pericia numa porta de entrada.

Por que esta lista nao reaproveita `INTERNAL_NETWORKS`
-----------------------------------------------------
O analisador de URL tem a propria lista de redes internas, e ela e
deliberadamente ESTREITA: existe para *relatar* "este endereco e de rede
privada" sem marcar a toa faixas de documentacao.

Aqui a exigencia e invertida. Esta lista existe para *defender*, e uma faixa
esquecida e um buraco. Por isso ela e a mais ampla possivel - e por isso nao
da para compartilhar a outra. Mesmo conceito, requisitos opostos.
"""

from __future__ import annotations

# Unicos esquemas que podem ser seguidos.
#
# Um redirecionamento para `file://`, `gopher://` ou `ftp://` nao tem uso
# legitimo aqui e cada um ja foi vetor de ataque em alguma biblioteca.
ALLOWED_REDIRECT_SCHEMES = frozenset({"http", "https"})

# Teto de saltos.
#
# Cadeias longas existem de verdade - encurtador aponta para encurtador - mas
# acima disto e laco, ou alguem tentando esgotar o tempo do servidor.
MAX_REDIRECT_HOPS = 10

# Segundos para conectar e para receber os cabecalhos de UM salto.
HOP_TIMEOUT_SECONDS = 5.0

# Teto do tempo total da cadeia inteira.
#
# Sem ele, dez saltos de quatro segundos cada passariam de quarenta, e quem
# esta esperando ja teria desistido.
TOTAL_TIMEOUT_SECONDS = 15.0

# Identificacao enviada nas requisicoes.
#
# Dizer quem somos e deliberado. A ferramenta ja avisa na tela que resolver o
# destino revela a investigacao a quem montou o link; fingir ser um navegador
# para esconder isso seria contradizer o proprio aviso.
RESOLVER_USER_AGENT = "ForensicGuard/1.0 (+static triage; redirect resolution)"
