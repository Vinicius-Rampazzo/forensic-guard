/**
 * Strings legiveis e artefatos encontrados dentro da evidencia.
 *
 * Duas secoes com propositos diferentes:
 *
 * - **Artefatos**: o que tem valor forense. URLs, IPs, caminhos, comandos.
 *   Vem sempre completos, mesmo quando a listagem crua foi cortada.
 * - **Strings**: o texto bruto. Pode ter dezenas de milhares de entradas, e
 *   por isso tem busca - uma lista desse tamanho sem filtro nao serve para
 *   nada, porque procurar algo especifico nela vira sorte.
 */

"use client";

import { useMemo, useState } from "react";

import { Card } from "@/components/Card";
import type { Artifacts, StringsAnalysis } from "@/types/analysis";

/** Rotulo legivel de cada categoria de artefato. */
const ARTIFACT_LABELS: Record<keyof Artifacts, string> = {
  urls: "URLs",
  ipv4: "IPv4 addresses",
  ipv6: "IPv6 addresses",
  emails: "Email addresses",
  windows_paths: "Windows paths",
  suspicious_keywords: "Command interpreters and techniques",
};

/**
 * Quantas linhas sao efetivamente desenhadas na tela.
 *
 * O navegador aguenta guardar 50.000 strings em memoria sem esforco, mas
 * desenhar 50.000 elementos no DOM trava a pagina. O limite e de RENDERIZACAO,
 * nao de dados: a busca percorre a lista inteira, e apenas o resultado
 * visivel e cortado.
 */
const MAX_RENDERED_ROWS = 500;

export function StringsPanel({ strings }: { strings: StringsAnalysis }) {
  const categories = Object.entries(strings.artifacts).filter(
    ([, values]) => Array.isArray(values) && values.length > 0,
  ) as [keyof Artifacts, string[]][];

  return (
    <div className="flex flex-col gap-4">
      <Card
        title="Artifacts"
        hint="Patterns recognised inside the file. Always complete, even when the listing below is cut short."
      >
        {categories.length === 0 ? (
          <p className="text-sm text-zinc-500 dark:text-zinc-400">
            No recognisable artifacts found.
          </p>
        ) : (
          <div className="flex flex-col gap-4">
            {categories.map(([category, values]) => (
              <div key={category} className="flex flex-col gap-1.5">
                <h4 className="text-xs font-medium text-zinc-500 dark:text-zinc-400">
                  {ARTIFACT_LABELS[category]} ({values.length})
                </h4>
                <ul className="flex flex-col gap-1">
                  {values.map((value) => (
                    <li
                      key={value}
                      className="rounded bg-zinc-50 px-2 py-1 font-mono text-[11px] break-all dark:bg-zinc-900/60"
                    >
                      {value}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        )}
      </Card>

      <SearchableStrings strings={strings} />
    </div>
  );
}

function SearchableStrings({ strings }: { strings: StringsAnalysis }) {
  const [query, setQuery] = useState("");

  const trimmed = query.trim().toLowerCase();

  // useMemo porque filtrar 50.000 strings a cada re-renderizacao seria
  // desperdicio: o calculo so precisa refazer quando a busca ou a lista mudam.
  const matches = useMemo(() => {
    if (!trimmed) return strings.sample;
    return strings.sample.filter((value) => value.toLowerCase().includes(trimmed));
  }, [trimmed, strings.sample]);

  const visible = matches.slice(0, MAX_RENDERED_ROWS);
  const hidden = matches.length - visible.length;

  return (
    <Card
      title="Extracted strings"
      hint={
        strings.truncated
          ? `${strings.total.toLocaleString("en-US")} found, ${strings.returned.toLocaleString("en-US")} listed — ${strings.truncation_reason ?? "the listing is partial"}.`
          : `${strings.total.toLocaleString("en-US")} strings found.`
      }
    >
      {strings.truncated && (
        <p className="mb-3 rounded border border-sky-500/30 bg-sky-500/5 px-3 py-2 text-xs text-sky-700 dark:text-sky-300">
          Only this listing is cut short. Hashes, entropy, type detection and
          the artifacts above cover the whole file.
        </p>
      )}

      {strings.sample.length === 0 ? (
        <p className="text-sm text-zinc-500 dark:text-zinc-400">
          No readable strings found.
        </p>
      ) : (
        <div className="flex flex-col gap-2">
          <div className="flex flex-wrap items-center gap-3">
            <input
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Filter strings — try http, .exe, powershell"
              aria-label="Filter extracted strings"
              className="min-w-0 flex-1 rounded-md border border-zinc-300 bg-transparent px-3 py-1.5 font-mono text-xs outline-none focus:border-emerald-500 dark:border-zinc-700"
            />

            {/*
              aria-live para que o leitor de tela anuncie quantos resultados
              a busca encontrou. Sem isso, quem nao enxerga digita e nao
              recebe retorno nenhum.
            */}
            <span
              aria-live="polite"
              className="shrink-0 font-mono text-[11px] text-zinc-500 tabular-nums dark:text-zinc-400"
            >
              {trimmed
                ? `${matches.length.toLocaleString("en-US")} match${matches.length === 1 ? "" : "es"}`
                : `${strings.sample.length.toLocaleString("en-US")} strings`}
            </span>
          </div>

          {matches.length === 0 ? (
            <p className="rounded border border-zinc-100 px-3 py-6 text-center text-sm text-zinc-500 dark:border-zinc-900 dark:text-zinc-400">
              Nothing matches {`"${query}"`}.
            </p>
          ) : (
            <>
              <ul className="max-h-[32rem] overflow-y-auto rounded border border-zinc-100 dark:border-zinc-900">
                {visible.map((value, index) => (
                  // O indice entra na chave porque a lista pode conter a mesma
                  // string em posicoes diferentes apos o filtro.
                  <li
                    key={`${index}-${value}`}
                    className="border-b border-zinc-100 px-2 py-1 font-mono text-[11px] break-all last:border-0 dark:border-zinc-900"
                  >
                    {highlight(value, trimmed)}
                  </li>
                ))}
              </ul>

              {hidden > 0 && (
                <p className="text-[11px] text-zinc-500 dark:text-zinc-400">
                  Showing the first {MAX_RENDERED_ROWS.toLocaleString("en-US")} of{" "}
                  {matches.length.toLocaleString("en-US")}. Refine the filter to
                  narrow it down — the search covers every string, not just the
                  ones drawn here.
                </p>
              )}
            </>
          )}
        </div>
      )}
    </Card>
  );
}

/**
 * Destaca o trecho buscado dentro da string.
 *
 * Feito com split em vez de innerHTML: o conteudo vem de um arquivo nao
 * confiavel, e injetar HTML a partir dele seria abrir um buraco de XSS dentro
 * de uma ferramenta de seguranca.
 */
function highlight(value: string, term: string) {
  if (!term) return value;

  const position = value.toLowerCase().indexOf(term);

  if (position === -1) return value;

  return (
    <>
      {value.slice(0, position)}
      <mark className="bg-emerald-500/30 text-inherit">
        {value.slice(position, position + term.length)}
      </mark>
      {value.slice(position + term.length)}
    </>
  );
}
