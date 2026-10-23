/**
 * Entrega as traducoes para cada requisicao, do lado do servidor.
 *
 * O `next-intl` chama esta funcao antes de renderizar, passando o idioma que
 * leu da URL. Devolvemos o dicionario correspondente, e a partir dai qualquer
 * componente - Server ou Client - enxerga as mensagens certas.
 *
 * O idioma recebido e validado contra a lista em `routing.ts`. Ele chega da
 * URL, e URL e entrada do usuario: `/xx-YY` ou `/../../etc/passwd` sao
 * perfeitamente digitaveis. Sem a validacao, o `import` dinamico abaixo
 * receberia um caminho construido por quem fez a requisicao.
 */

import { hasLocale } from "next-intl";
import { getRequestConfig } from "next-intl/server";

import { routing } from "./routing";

export default getRequestConfig(async ({ requestLocale }) => {
  const requested = await requestLocale;
  const locale = hasLocale(routing.locales, requested)
    ? requested
    : routing.defaultLocale;

  return {
    locale,
    messages: (await import(`../messages/${locale}.json`)).default,
  };
});
