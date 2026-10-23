/**
 * Fornece as traducoes para a aplicacao inteira.
 *
 * O `next-intl` costuma ser configurado com rotas por idioma - `/en`, `/pt` -
 * e o idioma resolvido no servidor. Aqui ele e usado no modo cliente, porque
 * a preferencia mora no localStorage, que so existe no navegador.
 *
 * A consequencia conhecida: o servidor sempre renderiza em ingles, e quem
 * escolheu portugues ve um instante do idioma padrao no primeiro quadro. O
 * preco de guardar a preferencia no localStorage em vez de num cookie, que o
 * servidor conseguiria ler.
 */

"use client";

import { NextIntlClientProvider } from "next-intl";
import { type ReactNode, useSyncExternalStore } from "react";

import en from "@/messages/en.json";
import ptBR from "@/messages/pt-BR.json";
import {
  type Locale,
  readLocale,
  readServerLocale,
  subscribeToLocale,
} from "@/i18n/locale-store";

/**
 * Os dicionarios sao importados estaticamente, nao carregados sob demanda.
 *
 * Sao dois idiomas e poucos kilobytes - um carregamento dinamico adicionaria
 * um estado de espera e um ponto de falha para economizar quase nada.
 */
const MESSAGES = {
  en,
  "pt-BR": ptBR,
} as const;

/** Le o idioma atual do localStorage, acompanhando mudancas. */
export function useLocale(): Locale {
  return useSyncExternalStore(subscribeToLocale, readLocale, readServerLocale);
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const locale = useLocale();

  return (
    <NextIntlClientProvider
      locale={locale}
      messages={MESSAGES[locale]}
      // Sem fuso definido, o next-intl avisa no console ao formatar datas.
      // Usar o do navegador e o comportamento esperado numa ferramenta local.
      timeZone={
        typeof Intl !== "undefined"
          ? Intl.DateTimeFormat().resolvedOptions().timeZone
          : "UTC"
      }
    >
      {children}
    </NextIntlClientProvider>
  );
}
