/**
 * Gera `/sitemap.xml`.
 *
 * Sao quatro URLs: duas paginas em dois idiomas. Um site deste tamanho e
 * descoberto por links de qualquer jeito, mas o sitemap carrega algo que o
 * rastreamento sozinho nao descobre - a relacao entre as versoes em cada
 * lingua, declarada em `alternates`.
 *
 * Escrito a partir da lista de idiomas em `routing`, e nao a mao: acrescentar
 * um terceiro idioma passa a aparecer aqui sem ninguem lembrar deste arquivo.
 */

import type { MetadataRoute } from "next";

import { routing } from "@/i18n/routing";

import { SITE_URL } from "./site";

/** Caminhos sem o prefixo de idioma, com a importancia relativa de cada um. */
const PAGES = [
  { path: "", priority: 1 },
  { path: "/analyze", priority: 0.8 },
];

/** Mapa de idioma para URL, que vira o `hreflang` de cada entrada. */
function alternatesFor(path: string): Record<string, string> {
  return Object.fromEntries(
    routing.locales.map((locale) => [locale, `${SITE_URL}/${locale}${path}`]),
  );
}

export default function sitemap(): MetadataRoute.Sitemap {
  const lastModified = new Date();

  return routing.locales.flatMap((locale) =>
    PAGES.map(({ path, priority }) => ({
      url: `${SITE_URL}/${locale}${path}`,
      lastModified,
      changeFrequency: "monthly" as const,
      priority,
      alternates: { languages: alternatesFor(path) },
    })),
  );
}
