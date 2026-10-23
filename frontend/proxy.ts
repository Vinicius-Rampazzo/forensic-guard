/**
 * Decide o idioma de quem chega sem prefixo na URL.
 *
 * Quem abre `http://localhost:3000` nao escolheu idioma nenhum. Este arquivo
 * roda antes da pagina, resolve isso e redireciona para `/en-us` ou `/pt-br`.
 *
 * A ordem que ele usa: primeiro o cookie `NEXT_LOCALE`, gravado quando a
 * pessoa troca de idioma no botao; depois o cabecalho `Accept-Language`, que o
 * navegador manda com o idioma do sistema; por fim o padrao da aplicacao. Ou
 * seja, a escolha e lembrada entre visitas, mesmo com o idioma morando na URL.
 *
 * O nome do arquivo e `proxy.ts`, nao `middleware.ts`: o Next 16 renomeou a
 * convencao e avisa no build quem usa o nome antigo. O conteudo e o mesmo.
 *
 * O `matcher` existe para isto nao rodar onde nao deve. Sem ele, cada imagem,
 * fonte e arquivo do `_next` passaria por aqui - custo inutil, e no caso dos
 * assets um redirecionamento que quebraria o carregamento.
 */

import createMiddleware from "next-intl/middleware";

import { routing } from "./i18n/routing";

export default createMiddleware(routing);

export const config = {
  // Tudo, menos as rotas internas do Next e qualquer caminho que tenha ponto
  // no nome - que e como se reconhece um arquivo (`logo.png`, `favicon.ico`).
  matcher: "/((?!api|_next|_vercel|.*\\..*).*)",
};
