/**
 * Cabecalho do relatorio: nome do arquivo, pontuacao e disclaimer.
 *
 * O desenho e deliberadamente contido. O score e uma heuristica de triagem, e
 * uma tela alarmista afirmaria mais certeza do que a ferramenta tem - alem de
 * contradizer o disclaimer que a propria API devolve em toda resposta.
 */

import { Badge } from "@/components/Badge";
import type { Risk, RiskLevel } from "@/types/analysis";

/** Cor da barra de progresso, por faixa de risco. */
const BAR_COLORS: Record<RiskLevel, string> = {
  low: "bg-emerald-500",
  medium: "bg-amber-500",
  high: "bg-orange-500",
  critical: "bg-red-500",
};

interface RiskScoreProps {
  filename: string;
  risk: Risk;
  disclaimer: string;
}

export function RiskScore({ filename, risk, disclaimer }: RiskScoreProps) {
  const scored = risk.indicators.filter((indicator) => indicator.score > 0).length;
  const informational = risk.indicators.length - scored;

  return (
    <header className="flex flex-col gap-4 rounded-lg border border-zinc-200 p-5 dark:border-zinc-800">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <h2 className="min-w-0 font-mono text-sm break-all">{filename}</h2>
        <Badge label={risk.level} tone={risk.level} />
      </div>

      <div className="flex items-baseline gap-2">
        <span className="text-5xl font-semibold tabular-nums">{risk.score}</span>
        <span className="text-sm text-zinc-500 dark:text-zinc-400">/ 100</span>
      </div>

      {/*
        role="progressbar" com os valores min/max/now faz a barra significar
        algo para leitores de tela. Sem isso, ela seria apenas uma faixa
        colorida invisivel para quem nao enxerga.
      */}
      <div
        role="progressbar"
        aria-valuenow={risk.score}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="Risk score"
        className="h-1.5 w-full overflow-hidden rounded-full bg-zinc-200 dark:bg-zinc-800"
      >
        <div
          className={`h-full rounded-full transition-all ${BAR_COLORS[risk.level]}`}
          style={{ width: `${risk.score}%` }}
        />
      </div>

      <p className="text-xs text-zinc-500 dark:text-zinc-400">
        {scored === 0 && informational === 0
          ? "No indicators found."
          : `${scored} scored indicator${scored === 1 ? "" : "s"}` +
            (informational > 0 ? `, ${informational} informational` : "")}
      </p>

      <p className="border-t border-zinc-100 pt-3 text-xs text-zinc-400 dark:border-zinc-900 dark:text-zinc-600">
        {disclaimer}
      </p>
    </header>
  );
}
