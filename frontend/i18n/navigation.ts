/**
 * Navegacao que carrega o idioma sozinha.
 *
 * Estes substituem o `Link` e o `useRouter` do Next em toda a aplicacao. A
 * diferenca: eles recebem caminhos SEM o prefixo de idioma - `/analyze` - e
 * acrescentam o idioma atual na hora de montar a URL.
 *
 * Isso evita o erro mais comum deste tipo de roteamento, que e escrever
 * `href="/analyze"` no JSX e jogar quem estava em portugues de volta para o
 * ingles sem ninguem perceber.
 *
 * `usePathname` tambem devolve o caminho sem o prefixo, que e exatamente o que
 * o alternador de idioma precisa para trocar de lingua sem sair da pagina.
 */

import { createNavigation } from "next-intl/navigation";

import { routing } from "./routing";

export const { Link, redirect, usePathname, useRouter, getPathname } =
  createNavigation(routing);
