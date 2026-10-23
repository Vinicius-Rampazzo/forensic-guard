/**
 * Cabecalho fixo do relatorio: arquivo, score e identificacao.
 *
 * Fica grudado no topo durante a rolagem porque, ao descer por centenas de
 * linhas de strings, e facil esquecer de qual arquivo se trata e qual foi a
 * nota - e e exatamente essa informacao que da sentido a tudo abaixo.
 *
 * O desenho e contido. O score e uma heuristica de triagem; uma tela
 * alarmista afirmaria mais certeza do que a ferramenta tem.
 */

import { RISK_BAR_COLORS, SeverityBadge } from "@/components/SeverityBadge";
import { formatBytes } from "@/components/format";
import { Card, CardContent } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import type { Detection, Risk } from "@/types/analysis";

interface RiskSummaryProps {
  filename: string;
  risk: Risk;
  detection: Detection;
  size: number;
  disclaimer: string;
}

export function RiskSummary({
  filename,
  risk,
  detection,
  size,
  disclaimer,
}: RiskSummaryProps) {
  const scored = risk.indicators.filter((indicator) => indicator.score > 0).length;
  const informational = risk.indicators.length - scored;

  return (
    <Card className="fg-card sticky top-4 z-10 backdrop-blur supports-[backdrop-filter]:bg-card/85">
      <CardContent className="flex flex-col gap-4">
        <div className="flex flex-wrap items-start justify-between gap-x-6 gap-y-3">
          <div className="flex min-w-0 flex-col gap-1">
            <h2 className="flex min-w-0 items-center gap-2 font-mono text-sm break-all">
              <span
                aria-hidden
                className="h-3.5 w-0.5 shrink-0 rounded-full"
                style={{ background: "var(--brand-cyan)" }}
              />
              {filename}
            </h2>
            <p className="text-xs text-muted-foreground">
              {detection.detected_name ?? "unrecognised format"} · {formatBytes(size)}
            </p>
          </div>

          <div className="flex items-center gap-4">
            <div className="flex items-baseline gap-1.5">
              <span className="text-4xl leading-none font-semibold tabular-nums">
                {risk.score}
              </span>
              <span className="text-xs text-muted-foreground">/ 100</span>
            </div>
            <SeverityBadge tone={risk.level} />
          </div>
        </div>

        {/*
          role="progressbar" com os valores faz a barra significar algo para
          leitores de tela. Sem isso ela e apenas uma faixa colorida invisivel
          para quem nao enxerga.
        */}
        <div
          role="progressbar"
          aria-valuenow={risk.score}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label="Risk score"
          className="h-1.5 w-full overflow-hidden rounded-full bg-muted"
        >
          <div
            className={`h-full rounded-full transition-[width] duration-700 ease-out ${RISK_BAR_COLORS[risk.level]}`}
            style={{ width: `${risk.score}%` }}
          />
        </div>

        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
          <span>
            {scored === 0 && informational === 0
              ? "No indicators found"
              : `${scored} scored indicator${scored === 1 ? "" : "s"}` +
                (informational > 0 ? ` · ${informational} informational` : "")}
          </span>
        </div>

        <Separator />

        <p className="text-[11px] text-muted-foreground">{disclaimer}</p>
      </CardContent>
    </Card>
  );
}
