/**
 * Quais idiomas existem e qual e o padrao.
 *
 * Esta e a unica fonte de verdade sobre idioma na aplicacao. O middleware, o
 * carregamento dos dicionarios e os componentes de navegacao todos leem deste
 * mesmo objeto - adicionar um terceiro idioma e mexer aqui e criar o arquivo
 * em `messages/`.
 *
 * Por que o idioma vive na URL
 * ----------------------------
 * A versao anterior guardava a preferencia no localStorage, que so existe no
 * navegador. O servidor montava o HTML sem saber o idioma, mandava em ingles,
 * e o React corrigia depois - dava um piscar visivel a cada recarga.
 *
 * Com o idioma na URL o servidor sabe antes de montar qualquer coisa. Mais que
 * isso: como `/pt-br` e `/en-us` sao rotas distintas, o Next gera as duas
 * prontas no build. Nao existe momento em que o idioma errado apareca, porque
 * o idioma errado nunca e enviado.
 *
 * Por que tudo minusculo
 * ----------------------
 * A convencao de BCP 47 escreve a regiao em maiuscula - `pt-BR`. Mas a
 * comparacao e definida como insensivel a maiusculas, e `pt-br` e igualmente
 * valido em `<html lang>` e no `Intl`. URL em minuscula e a pratica comum na
 * web, e evita o caso chato de alguem digitar `/pt-br` e receber 404.
 */

import { defineRouting } from "next-intl/routing";

export const routing = defineRouting({
  locales: ["en-us", "pt-br"],
  defaultLocale: "en-us",
});

export type Locale = (typeof routing.locales)[number];
