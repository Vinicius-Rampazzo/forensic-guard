import type { Metadata } from "next";
import { JetBrains_Mono, Space_Grotesk } from "next/font/google";

import { I18nProvider } from "@/components/I18nProvider";
import { TooltipProvider } from "@/components/ui/tooltip";

import "./globals.css";

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

// Metadata alimenta o <title> e as meta tags da pagina. Como layout.tsx e um
// Server Component, o Next resolve isso na renderizacao, sem JavaScript extra
// no navegador.
export const metadata: Metadata = {
  title: "ForensicGuard — Digital Evidence Analyzer",
  description:
    "Open-source forensic triage tool for inspecting files, images and emails for suspicious indicators, metadata anomalies and potential security threats.",
};

/**
 * Aplica o tema salvo ANTES de a pagina ser desenhada.
 *
 * Sem isto existe o problema conhecido como FOUC - o flash de tema errado. A
 * pagina chega do servidor sem saber a preferencia de quem abre, pinta clara,
 * e so depois o React assume e troca para escuro. O usuario ve um piscar
 * branco a cada carregamento.
 *
 * `dangerouslySetInnerHTML` assusta pelo nome, mas aqui o conteudo e uma
 * constante escrita por nos - nenhum dado externo entra nesta string. O
 * atributo existe porque o React, por padrao, escapa o conteudo de <script>.
 *
 * O script roda de forma sincrona no <head>, antes de qualquer pintura.
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

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    // A classe `dark` ja vem marcada no HTML do servidor porque o tema escuro
    // e o padrao da ferramenta. O script acima so a remove quando a pessoa
    // escolheu claro explicitamente.
    <html
      lang="en"
      className={`dark ${spaceGrotesk.variable} ${jetbrainsMono.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body className="flex min-h-full flex-col">
        <I18nProvider>
          <TooltipProvider delayDuration={300}>{children}</TooltipProvider>
        </I18nProvider>
      </body>
    </html>
  );
}
