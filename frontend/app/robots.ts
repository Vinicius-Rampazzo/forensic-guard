/**
 * Gera `/robots.txt`.
 *
 * Em codigo, e nao como arquivo estatico em `public/`, porque o endereco do
 * sitemap precisa ser absoluto e muda conforme o ambiente. Um arquivo fixo
 * apontaria para o dominio de producao mesmo num preview.
 */

import type { MetadataRoute } from "next";

import { SITE_URL } from "./site";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
    },
    sitemap: `${SITE_URL}/sitemap.xml`,
    host: SITE_URL,
  };
}
