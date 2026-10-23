/**
 * Campo para colar uma URL e analisar.
 *
 * Um formulario de verdade, com <form> e submit: assim Enter funciona sem
 * nenhum manipulador de teclado, que e o comportamento que todo mundo ja
 * espera de um campo de texto com botao ao lado.
 */

"use client";

import { Link2, Search, ShieldOff } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const EXAMPLES = [
  "http://banco.com.br@203.0.113.45/login",
  "https://bit.ly/3xYzAbC",
  "http://empresa.com.br.seguranca.tk/conta",
];

interface UrlInputProps {
  onSubmit: (url: string) => void;
  disabled?: boolean;
}

export function UrlInput({ onSubmit, disabled = false }: UrlInputProps) {
  const t = useTranslations("url");
  const [value, setValue] = useState("");

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();

    const trimmed = value.trim();

    if (trimmed) {
      onSubmit(trimmed);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="flex flex-col items-center gap-5 rounded-xl border-2 border-dashed px-6 py-14 text-center transition-colors duration-200 hover:border-foreground/25"
    >
      <div className="flex size-12 items-center justify-center rounded-full border bg-muted/40">
        <Link2 className="size-5 text-muted-foreground" />
      </div>

      <div className="flex flex-col gap-1">
        <p className="text-base font-medium">{t("paste")}</p>
        <p className="text-sm text-muted-foreground">{t("neverVisited")}</p>
      </div>

      <div className="flex w-full max-w-xl flex-col gap-2 sm:flex-row">
        <Input
          type="url"
          inputMode="url"
          value={value}
          onChange={(event) => setValue(event.target.value)}
          placeholder="https://..."
          aria-label={t("paste")}
          disabled={disabled}
          // spellCheck e autoCorrect desligados: o corretor do navegador
          // adora "consertar" URLs, trocando pontuacao e quebrando o endereco
          // antes de ele chegar na analise.
          spellCheck={false}
          autoCorrect="off"
          autoCapitalize="off"
          className="flex-1 font-mono text-sm"
        />

        <Button type="submit" disabled={disabled || !value.trim()} className="gap-2">
          <Search className="size-4" />
          {t("analyse")}
        </Button>
      </div>

      <div className="flex flex-col items-center gap-2">
        <p className="text-[11px] text-muted-foreground">{t("tryOne")}</p>
        <div className="flex flex-wrap justify-center gap-1.5">
          {EXAMPLES.map((example) => (
            <button
              key={example}
              type="button"
              onClick={() => setValue(example)}
              disabled={disabled}
              className="rounded border px-2 py-1 font-mono text-[10px] text-muted-foreground transition-colors duration-200 hover:border-foreground/40 hover:text-foreground"
            >
              {example}
            </button>
          ))}
        </div>
      </div>

      <p className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
        <ShieldOff className="size-3.5" />
        {t("noRequest")}
      </p>
    </form>
  );
}
