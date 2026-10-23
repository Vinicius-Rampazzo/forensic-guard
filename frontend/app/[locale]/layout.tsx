/**
 * Casca da aplicacao, dentro do segmento de idioma.
 *
 * Este arquivo era `app/layout.tsx`. Mudou de lugar porque o idioma agora vive
 * na URL, e por isso o `lang` do <html> finalmente pode estar correto: antes
 * ficava fixo em "en" mesmo quando a interface estava em portugues, o que
 * atrapalha leitor de tela e corretor ortografico do navegador.
 *
 * Cabecalho e rodape ficam aqui, e nao nas paginas. Como sao rotas de verdade,
 * o Next mantem o layout montado ao navegar - a barra de cima nao pisca na
 * troca entre o institucional e a ferramenta.
 */

import { hasLocale, NextIntlClientProvider } from "next-intl";
import { getTranslations, setRequestLocale } from "next-intl/server";
import type { Metadata } from "next";
import { JetBrains_Mono, Space_Grotesk } from "next/font/google";
import { notFound } from "next/navigation";
import type { ReactNode } from "react";

import { AppHeader } from "@/components/AppHeader";
import { SiteFooter } from "@/components/SiteFooter";
import { TooltipProvider } from "@/components/ui/tooltip";
import { routing } from "@/i18n/routing";

import "../globals.css";

/**
 * Space Grotesk para a interface.
 *
 * Geometrica e levemente angular, acompanha a forma da logo. Tem personalidade
 * suficiente para dar identidade sem atrapalhar a leitura de texto corrido -
 * ao contrario das fontes "tecnologicas" mais conhecidas, que viram ruido
 * visual em paragrafo.
 */
const spaceGrotesk = Space_Grotesk({
  variable: "--font-space-grotesk",
  subsets: ["latin"],
  display: "swap",
});

/**
 * JetBrains Mono para dados tecnicos.
 *
 * Hashes, caminhos e strings extraidas precisam de largura fixa para alinhar
 * em coluna. Esta tem o zero cortado e distingue bem 1, l e I - o que importa
 * quando alguem compara um hash caractere a caractere.
 */
const jetbrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains-mono",
  subsets: ["latin"],
  display: "swap",
});

/**
 * Titulo e descricao da aba, por idioma.
 *
 * Eram constantes em ingles. Com duas rotas de idioma isso significava que
 * `/pt-br` se anunciava em ingles para buscadores e para a aba do navegador -
 * justamente os dois lugares onde o texto e lido fora da pagina.
 */
export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;

  const resolved = hasLocale(routing.locales, locale) ? locale : routing.defaultLocale;
  const t = await getTranslations({ locale: resolved, namespace: "meta" });

  return {
    title: t("title"),
    description: t("description"),
  };
}

/**
 * Lista os idiomas para o Next gerar uma pagina pronta para cada um no build.
 *
 * E isto que elimina o piscar de idioma: `/pt-br` ja existe como HTML escrito
 * em portugues antes de alguem abrir o navegador.
 */
export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

/**
 * Aplica o tema salvo ANTES de a pagina ser desenhada.
 *
 * Sem isto existe o problema conhecido como FOUC - o flash de tema errado. A
 * pagina chega do servidor sem saber a preferencia de quem abre, pinta clara,
 * e so depois o React assume e troca para escuro. O usuario ve um piscar
 * branco a cada carregamento.
 *
 * O mesmo problema existia no idioma, e foi resolvido de outra forma: idioma
 * virou rota. Tema nao pode virar rota - ninguem quer dois enderecos para a
 * mesma pagina so por causa da cor de fundo - entao aqui o script continua
 * sendo a resposta certa.
 *
 * `dangerouslySetInnerHTML` assusta pelo nome, mas aqui o conteudo e uma
 * constante escrita por nos - nenhum dado externo entra nesta string. O
 * atributo existe porque o React, por padrao, escapa o conteudo de <script>.
 */
const THEME_SCRIPT = `
try {
  var stored = localStorage.getItem("forensicguard-theme");
  var dark = stored ? stored === "dark" : true;
  document.documentElement.classList.toggle("dark", dark);
} catch (e) {
  document.documentElement.classList.add("dark");
}
`;

/**
 * Rede de seguranca para quem navega sem JavaScript.
 *
 * As secoes institucionais sao animadas pelo `motion`, que as entrega com
 * `opacity: 0` no HTML e as revela quando entram na tela. Sem JavaScript nada
 * as revelaria, e a pagina ficaria em branco abaixo da dobra.
 *
 * A ferramenta em si nao funciona sem JavaScript - ela depende de upload e
 * `fetch`. Mas o institucional e so texto, e texto que existe no HTML deve
 * poder ser lido.
 */
const NOSCRIPT_REVEAL = `
[data-reveal] * {
  opacity: 1 !important;
  transform: none !important;
}
`;

export default async function LocaleLayout({
  children,
  params,
}: {
  children: ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;

  // O idioma chega da URL, e URL e entrada do usuario. `/xx` e digitavel.
  if (!hasLocale(routing.locales, locale)) {
    notFound();
  }

  // Autoriza a renderizacao estatica desta rota. Sem esta chamada o next-intl
  // trata a pagina como dinamica, e voltariamos a montar o HTML por
  // requisicao - perdendo justamente o ganho de ter o idioma na URL.
  setRequestLocale(locale);

  return (
    // A classe `dark` ja vem marcada no HTML do servidor porque o tema escuro
    // e o padrao da ferramenta. O script acima so a remove quando a pessoa
    // escolheu claro explicitamente.
    <html
      lang={locale}
      className={`dark ${spaceGrotesk.variable} ${jetbrainsMono.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
        <noscript>
          <style>{NOSCRIPT_REVEAL}</style>
        </noscript>
      </head>
      <body className="flex min-h-full flex-col">
        <NextIntlClientProvider>
          <TooltipProvider delayDuration={300}>
            <AppHeader />
            {children}
            <SiteFooter />
          </TooltipProvider>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
