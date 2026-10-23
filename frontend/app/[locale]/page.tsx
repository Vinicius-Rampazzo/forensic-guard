/**
 * Rota institucional: `/pt-br` e `/en-us`.
 *
 * Esta pagina e Server Component de proposito, e bem fina. O trabalho dela e
 * autorizar a renderizacao estatica para o idioma da URL e compor as duas
 * partes do institucional. Todo o resto - estado, animacao, ponteiro - mora
 * nos componentes de cliente que ela monta.
 */

import { hasLocale } from "next-intl";
import { setRequestLocale } from "next-intl/server";
import { notFound } from "next/navigation";

import { LandingScreen } from "@/components/LandingScreen";
import { LandingSections } from "@/components/LandingSections";
import { routing } from "@/i18n/routing";

export default async function LandingPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;

  if (!hasLocale(routing.locales, locale)) {
    notFound();
  }

  setRequestLocale(locale);

  return (
    <main className="flex-1">
      {/*
        A dobra inicial fica fora do container de largura maxima, porque a
        grade de fundo dela precisa atravessar a tela de lado a lado.
      */}
      <LandingScreen />

      <div className="mx-auto w-full max-w-6xl px-6">
        <LandingSections />
      </div>
    </main>
  );
}
