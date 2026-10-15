"""Analise heuristica de URLs encontradas numa evidencia.

Esta e a versao minima do modulo: apenas o que o Risk Engine precisa agora.
As heuristicas restantes previstas na especificacao - subdominios em excesso,
URLs muito longas, presenca de `@`, encurtadores conhecidos, HTTP sem TLS -
chegam junto com a analise de e-mail, onde fazem mais diferenca.

Um aviso que vale para o modulo inteiro: **uma URL heuristicamente suspeita
nao e uma URL maliciosa.** Tudo aqui aponta caracteristicas incomuns, nao
intencao.
"""

from __future__ import annotations

import ipaddress
from urllib.parse import urlsplit

# Prefixo que identifica dominios codificados em punycode.
#
# Punycode representa caracteres nao-ASCII usando apenas ASCII, o que permite
# dominios em arabe, chines ou com acentuacao. E um mecanismo legitimo e
# amplamente usado - e tambem o que torna possivel registrar um dominio
# visualmente identico a uma marca conhecida, trocando uma letra latina por
# outra de aparencia igual em outro alfabeto.
PUNYCODE_PREFIX = "xn--"


def extract_host(url: str) -> str | None:
    """Devolve o host de uma URL, ou None quando nao da para determinar.

    URLs vem de dentro de arquivos nao confiaveis e frequentemente estao
    truncadas ou malformadas. Qualquer falha de parsing vira None, nunca
    excecao: uma URL quebrada no meio de um binario nao pode derrubar a
    analise.
    """
    try:
        host = urlsplit(url).hostname
    except ValueError:
        # urlsplit levanta ValueError em casos como porta invalida ou
        # colchetes desbalanceados em endereco IPv6.
        return None

    return host or None


def has_ip_address_host(url: str) -> bool:
    """Diz se a URL aponta para um endereco IP em vez de um dominio.

    Nao e prova de nada - servicos internos e dispositivos de rede usam IP o
    tempo todo. Mas conteudo destinado a pessoas quase sempre usa nome de
    dominio, e usar IP evita registro e verificacao de reputacao.
    """
    host = extract_host(url)

    if host is None:
        return False

    try:
        ipaddress.ip_address(host)
    except ValueError:
        return False

    return True


def has_punycode_domain(url: str) -> bool:
    """Diz se alguma parte do dominio esta codificada em punycode.

    A verificacao e por rotulo (`a.xn--80ak6aa92e.com`), e nao por "contem a
    string": assim `meu-xn--site.com`, que apenas contem esses caracteres no
    meio de uma palavra, nao e marcado.
    """
    host = extract_host(url)

    if host is None:
        return False

    return any(label.startswith(PUNYCODE_PREFIX) for label in host.split("."))


def find_ip_address_urls(urls: list[str]) -> list[str]:
    """Filtra as URLs que apontam para endereco IP."""
    return [url for url in urls if has_ip_address_host(url)]


def find_punycode_urls(urls: list[str]) -> list[str]:
    """Filtra as URLs com dominio em punycode."""
    return [url for url in urls if has_punycode_domain(url)]
