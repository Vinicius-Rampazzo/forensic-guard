/**
 * Rota da ferramenta: `/pt-br/analyze` e `/en-us/analyze`.
 *
 * Separar o institucional da ferramenta nao e organizacao de pastas: muda o
 * que o navegador consegue fazer. A analise passa a ter endereco proprio, o
 * botao de voltar funciona, da para abrir em outra aba, e o scroll volta ao
 * topo sozinho na troca de pagina.
 */

import { hasLocale } from "next-intl";
import { setRequestLocale } from "next-intl/server";
import { notFound } from "next/navigation";

import { AnalyzeWorkbench } from "@/components/AnalyzeWorkbench";
import { routing } from "@/i18n/routing";

export default async function AnalyzePage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;

  if (!hasLocale(routing.locales, locale)) {
    notFound();
  }

  setRequestLocale(locale);

  return <AnalyzeWorkbench />;
}
