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

import { ApiHealthProvider } from "@/components/ApiHealthProvider";
import { AppHeader } from "@/components/AppHeader";
import { SiteFooter } from "@/components/SiteFooter";
import { StructuredData } from "@/components/StructuredData";
import { TooltipProvider } from "@/components/ui/tooltip";
import { routing } from "@/i18n/routing";

import { REPOSITORY_URL, SITE_NAME, SITE_URL } from "../site";
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
 * Converte `pt-br` para `pt_BR`, que e o formato que o Open Graph exige.
 *
 * O `hreflang` do HTML aceita `pt-br` em qualquer caixa; o Open Graph, nao.
 * Sao duas especificacoes diferentes lendo a mesma informacao, e e por isso
 * que o mesmo idioma aparece escrito de tres jeitos nesta pagina: `pt-br` na
 * URL, `pt-BR` no hreflang e `pt_BR` aqui.
 */
function toOpenGraphLocale(locale: string): string {
  const [language, region] = locale.split("-");

  return region ? `${language}_${region.toUpperCase()}` : language;
}

/**
 * Tudo o que esta pagina diz sobre si mesma fora dela.
 *
 * Isto alimenta tres leitores diferentes, e cada um le uma parte:
 *
 *   - a aba do navegador le o titulo;
 *   - o buscador le titulo, descricao, canonical e os idiomas alternativos;
 *   - a rede social le as marcas `og:` e `twitter:` para montar o cartao.
 *
 * Tudo sai por idioma. Com duas rotas, `/pt-br` se anunciando em ingles seria
 * errado nos tres lugares - e sao justamente os lugares onde o texto e lido
 * por quem ainda nao entrou no site.
 */
export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;

  const resolved = hasLocale(routing.locales, locale) ? locale : routing.defaultLocale;
  const t = await getTranslations({ locale: resolved, namespace: "meta" });

  const title = t("title");
  const description = t("description");

  return {
    /*
      Base para resolver os caminhos relativos abaixo. Sem ela o Next avisa no
      build e a imagem de preview sai como `/og-pt-br.png`, que o servidor do
      LinkedIn nao tem como resolver contra nada.
    */
    metadataBase: new URL(SITE_URL),

    title,
    description,
    applicationName: SITE_NAME,
    authors: [{ name: "Vinicius Rampazzo", url: REPOSITORY_URL }],
    creator: "Vinicius Rampazzo",

    alternates: {
      /*
        Canonical e hreflang existem por causa do mesmo problema: as duas
        rotas mostram o MESMO produto em linguas diferentes. Sem declarar a
        relacao, o buscador pode tratar uma como copia da outra e esconder
        alguma das duas. Com ela, entende que sao versoes e entrega cada uma a
        quem fala aquela lingua.

        `x-default` e para quem nao fala nenhuma das duas: manda para a raiz,
        onde o proxy decide pelo idioma do navegador.
      */
      canonical: `${SITE_URL}/${resolved}`,
      languages: {
        "en-US": `${SITE_URL}/en-us`,
        "pt-BR": `${SITE_URL}/pt-br`,
        "x-default": SITE_URL,
      },
    },

    openGraph: {
      type: "website",
      siteName: SITE_NAME,
      title,
      description,
      url: `${SITE_URL}/${resolved}`,
      /*
        O Open Graph usa sublinhado E regiao em maiuscula: `pt_BR`, nao
        `pt_br`. Trocar so o hifen por sublinhado nao basta - foi o que a
        primeira versao fazia, e saia um valor que nenhuma rede reconhece.
      */
      locale: toOpenGraphLocale(resolved),
      // Declarar a outra versao ajuda a rede a oferecer o idioma certo a quem
      // compartilha o link para um publico diferente.
      alternateLocale: routing.locales
        .filter((other) => other !== resolved)
        .map(toOpenGraphLocale),
      images: [
        {
          url: `/og-${resolved}.png`,
          width: 1200,
          height: 630,
          alt: `${SITE_NAME} — ${description}`,
        },
      ],
    },

    twitter: {
      // `summary_large_image` usa a imagem inteira; `summary` a corta num
      // quadradinho ao lado do texto, que desperdica a arte.
      card: "summary_large_image",
      title,
      description,
      images: [`/og-${resolved}.png`],
    },

    robots: {
      index: true,
      follow: true,
      googleBot: { index: true, follow: true, "max-image-preview": "large" },
    },

    category: "technology",
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

  // A mesma descricao que vai para o <meta>. Os dados estruturados precisam
  // dizer o mesmo que o resto da pagina: buscador compara, e divergencia entre
  // o que a marcacao afirma e o que a pagina mostra conta contra.
  const t = await getTranslations({ locale, namespace: "meta" });
  const description = t("description");

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
        <StructuredData locale={locale} description={description} />
        <noscript>
          <style>{NOSCRIPT_REVEAL}</style>
        </noscript>
      </head>
      <body className="flex min-h-full flex-col">
        <NextIntlClientProvider>
          <TooltipProvider delayDuration={300}>
            {/*
              A saude da API e consultada UMA vez, aqui, e compartilhada com
              quem precisar. O cabecalho e a bancada de analise liam o mesmo
              estado por conta propria antes disto, e com o botao de tentar
              novamente os dois passaram a poder discordar.
            */}
            <ApiHealthProvider>
              <AppHeader />
              {children}
              <SiteFooter />
            </ApiHealthProvider>
          </TooltipProvider>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
