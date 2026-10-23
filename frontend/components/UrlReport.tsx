/**
 * Relatorio de uma URL analisada.
 *
 * Mais simples que o relatorio de arquivo - uma URL nao tem hashes, entropia
 * nem strings - mas usa a mesma escala de risco e o mesmo formato de
 * indicador. E isso que faz "70 pontos" significar a mesma coisa nos dois
 * casos.
 */

"use client";

import { AlertTriangle, ShieldOff } from "lucide-react";
import { useTranslations } from "next-intl";

import { IndicatorsList } from "@/components/IndicatorsList";
import { RISK_BAR_COLORS, SeverityBadge } from "@/components/SeverityBadge";
import { UrlAnatomy } from "@/components/UrlAnatomy";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Card, CardContent } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import type { UrlAnalysisResult } from "@/types/analysis";

export function UrlReport({ result }: { result: UrlAnalysisResult }) {
  const t = useTranslations("url");
  const tRisk = useTranslations("risk");

  if (result.error) {
    return (
      <Alert variant="destructive" className="mx-auto max-w-2xl">
        <AlertTriangle />
        <AlertTitle>{t("couldNotParse")}</AlertTitle>
        <AlertDescription>{result.error}</AlertDescription>
      </Alert>
    );
  }

  const scored = result.risk.indicators.filter((indicator) => indicator.score > 0).length;

  return (
    <div className="flex flex-col gap-6">
      <Card className="fg-card">
        <CardContent className="flex flex-col gap-4">
          <div className="flex flex-wrap items-start justify-between gap-x-6 gap-y-3">
            <div className="flex min-w-0 flex-col gap-1">
              <h2 className="flex min-w-0 items-center gap-2 font-mono text-sm break-all">
                <span
                  aria-hidden
                  className="h-3.5 w-0.5 shrink-0 rounded-full"
                  style={{ background: "var(--brand-cyan)" }}
                />
                {result.parts.registrable_domain || result.parts.scheme}
              </h2>
              <p className="text-xs text-muted-foreground">
                {scored === 0
                  ? tRisk("noIndicators")
                  : tRisk("scoredIndicators", { count: scored })}
              </p>
            </div>

            <div className="flex items-center gap-4">
              <div className="flex items-baseline gap-1.5">
                <span className="text-4xl leading-none font-semibold tabular-nums">
                  {result.risk.score}
                </span>
                <span className="text-xs text-muted-foreground">/ 100</span>
              </div>
              <SeverityBadge tone={result.risk.level} />
            </div>
          </div>

          <div
            role="progressbar"
            aria-valuenow={result.risk.score}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label="Risk score"
            className="h-1.5 w-full overflow-hidden rounded-full bg-muted"
          >
            <div
              className={`h-full rounded-full transition-[width] duration-700 ease-out ${RISK_BAR_COLORS[result.risk.level]}`}
              style={{ width: `${result.risk.score}%` }}
            />
          </div>

          <Separator />

          {/*
            O disclaimer da URL e diferente do de arquivo e precisa ser lido.
            "Nada encontrado" aqui NAO significa destino seguro - significa
            que a estrutura do endereco nao tem nada de incomum. A pagina do
            outro lado nunca foi vista.
          */}
          <p className="flex items-start gap-2 text-[11px] text-muted-foreground">
            <ShieldOff className="mt-0.5 size-3.5 shrink-0" />
            {result.disclaimer}
          </p>
        </CardContent>
      </Card>

      <UrlAnatomy parts={result.parts} url={result.url} />

      <div className="flex flex-col gap-3">
        <h3 className="text-sm font-medium">
          {tRisk("title")} · {result.risk.indicators.length}
        </h3>
        <IndicatorsList indicators={result.risk.indicators} />
      </div>
    </div>
  );
}
