/**
 * Alternador de idioma.
 *
 * Com apenas dois idiomas, um botao que alterna entre eles e melhor que um
 * menu suspenso: menos cliques e nada escondido. Se um terceiro idioma
 * entrar, aqui vira um select.
 */

"use client";

import { Languages } from "lucide-react";

import { useLocale } from "@/components/I18nProvider";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { writeLocale } from "@/i18n/locale-store";

const LABELS = {
  en: "EN",
  "pt-BR": "PT",
} as const;

export function LanguageToggle() {
  const locale = useLocale();
  const next = locale === "en" ? "pt-BR" : "en";

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          // Escreve no localStorage e dispara o evento; o
          // useSyncExternalStore do provider percebe e re-renderiza tudo.
          // Nao ha setState aqui.
          onClick={() => writeLocale(next)}
          className="gap-1.5 px-2 font-mono text-[11px]"
          aria-label={`Switch to ${next === "en" ? "English" : "Português"}`}
        >
          <Languages className="size-3.5" />
          {LABELS[locale]}
        </Button>
      </TooltipTrigger>
      <TooltipContent>{next === "en" ? "English" : "Português (Brasil)"}</TooltipContent>
    </Tooltip>
  );
}
