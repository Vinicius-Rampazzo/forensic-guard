/**
 * Lista dos indicadores que produziram o score.
 *
 * E o componente mais importante do relatorio. Sem ele, o numero do Risk Score
 * seria uma afirmacao sem justificativa - e um relatorio forense nao pode ser
 * uma opiniao. Cada entrada mostra a regra, quantos pontos somou, e a
 * evidencia concreta, para que quem le possa conferir e discordar.
 */

import { Badge } from "@/components/Badge";
import type { Indicator } from "@/types/analysis";

export function IndicatorsList({ indicators }: { indicators: Indicator[] }) {
  if (indicators.length === 0) {
    return (
      <p className="rounded-lg border border-zinc-200 p-4 text-sm text-zinc-500 dark:border-zinc-800 dark:text-zinc-400">
        No indicators found. Static triage did not flag anything — which is not
        the same as saying the file is safe.
      </p>
    );
  }

  return (
    <ul className="flex flex-col gap-3">
      {indicators.map((indicator) => (
        <li
          key={indicator.id}
          className="rounded-lg border border-zinc-200 p-4 dark:border-zinc-800"
        >
          <div className="flex flex-wrap items-start justify-between gap-2">
            <h4 className="text-sm font-medium">{indicator.title}</h4>
            <div className="flex shrink-0 items-center gap-2">
              <Badge label={indicator.severity} tone={indicator.severity} />
              <span className="font-mono text-xs text-zinc-500 tabular-nums dark:text-zinc-400">
                {indicator.score > 0 ? `+${indicator.score}` : "0"}
              </span>
            </div>
          </div>

          <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-400">
            {indicator.description}
          </p>

          <p className="mt-2 font-mono text-[11px] text-zinc-400 dark:text-zinc-600">
            {indicator.id}
          </p>

          <Evidence evidence={indicator.evidence} />
        </li>
      ))}
    </ul>
  );
}

/**
 * Exibe a evidencia de um indicador.
 *
 * O formato varia por regra - umas trazem uma lista de URLs, outras um par de
 * extensoes, outras objetos aninhados. Em vez de um componente por formato,
 * uma renderizacao generica cobre todos: chave a esquerda, valor formatado a
 * direita.
 */
function Evidence({ evidence }: { evidence: Record<string, unknown> }) {
  const entries = Object.entries(evidence);

  if (entries.length === 0) return null;

  return (
    <dl className="mt-3 flex flex-col gap-1 rounded border border-zinc-100 bg-zinc-50 p-3 dark:border-zinc-900 dark:bg-zinc-900/40">
      {entries.map(([key, value]) => (
        <div key={key} className="flex flex-col gap-0.5 sm:flex-row sm:gap-3">
          <dt className="shrink-0 font-mono text-[11px] text-zinc-500 sm:w-40 dark:text-zinc-400">
            {key}
          </dt>
          <dd className="min-w-0 font-mono text-[11px] break-all">{formatValue(value)}</dd>
        </div>
      ))}
    </dl>
  );
}

/**
 * Converte qualquer valor de evidencia em texto legivel.
 *
 * Os valores vem do backend como JSON e podem ser numero, texto, lista ou
 * objeto. `JSON.stringify` cobre os casos aninhados sem precisar de um
 * tratamento especial por regra.
 */
function formatValue(value: unknown): string {
  if (value === null || value === undefined) return "—";

  if (Array.isArray(value)) {
    return value.map((item) => formatValue(item)).join(", ");
  }

  if (typeof value === "object") {
    return JSON.stringify(value);
  }

  if (typeof value === "number") {
    return value.toLocaleString("en-US");
  }

  return String(value);
}
