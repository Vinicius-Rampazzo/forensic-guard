/**
 * Alternador de idioma.
 *
 * Com apenas dois idiomas, um botao que alterna entre eles e melhor que um
 * menu suspenso: menos cliques e nada escondido. Se um terceiro idioma
 * entrar, aqui vira um select.
 *
 * Antes isto escrevia no localStorage. Agora troca a URL, porque o idioma
 * passou a viver nela - e e isso que faz o servidor mandar o HTML ja no idioma
 * certo, sem o piscar de ingles que existia a cada recarga.
 *
 * Por que o documento inteiro recarrega
 * -------------------------------------
 * A primeira versao usava o roteador do cliente, e isso trouxe um erro no
 * console: "Encountered a script tag while rendering React component".
 *
 * A causa: `/pt-br` e `/en-us` sao instancias diferentes do segmento
 * `[locale]`, entao navegar entre elas pelo cliente remonta o layout raiz - e
 * dentro dele esta o <script> que aplica o tema antes da pintura. Ao recriar
 * esse elemento no cliente, o React avisa (com razao) que script criado assim
 * nunca executa. O script ja tinha feito o trabalho dele na carga inicial, mas
 * o aviso e legitimo e nao se cala.
 *
 * Trocar de idioma muda o documento inteiro, incluindo o `lang` do <html>.
 * Pedir um documento novo e, portanto, a descricao honesta do que acontece -
 * e de quebra o layout raiz nunca e remontado pelo cliente.
 *
 * A preferencia continua sendo lembrada: o `proxy.ts` grava o cookie
 * `NEXT_LOCALE` em toda requisicao de documento cujo idioma difere do cookie.
 * Nao e preciso grava-lo aqui.
 */

"use client";

import { Languages } from "lucide-react";
import { useLocale } from "next-intl";

import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { getPathname, usePathname } from "@/i18n/navigation";
import type { Locale } from "@/i18n/routing";

const LABELS: Record<Locale, string> = {
  "en-us": "EN",
  "pt-br": "PT",
};

export function LanguageToggle() {
  const locale = useLocale() as Locale;

  // Caminho sem o prefixo de idioma - `/analyze`, nao `/pt-br/analyze`. E por
  // isso que trocar de lingua mantem a pessoa na mesma pagina.
  const pathname = usePathname();

  const next: Locale = locale === "en-us" ? "pt-br" : "en-us";

  function switchLocale() {
    // `replace` e nao `assign`: trocar de idioma nao e navegar para outro
    // lugar, entao nao deve criar uma entrada no historico. Sem isso, o botao
    // de voltar do navegador levaria a mesma pagina na lingua anterior.
    window.location.replace(getPathname({ href: pathname, locale: next }));
  }

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          onClick={switchLocale}
          className="gap-1.5 px-2 font-mono text-[11px]"
          aria-label={`Switch to ${next === "en-us" ? "English" : "Português"}`}
        >
          <Languages className="size-3.5" />
          {LABELS[locale]}
        </Button>
      </TooltipTrigger>
      <TooltipContent>{next === "en-us" ? "English" : "Português (Brasil)"}</TooltipContent>
    </Tooltip>
  );
}
