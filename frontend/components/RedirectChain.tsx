/**
 * Resolucao de redirecionamentos, sob pedido explicito.
 *
 * Tudo o mais na ferramenta e estatico, e isso esta escrito na tela. Este
 * componente e a excecao, e por isso ele nao resolve nada sozinho: mostra o
 * que a acao custa, espera o clique, e so entao faz a requisicao.
 *
 * O botao so aparece quando a analise ja apontou que o destino esta escondido
 * - encurtador conhecido ou endereco com forma de redirecionador. Oferecer
 * "resolver destino" em toda URL convidaria a contatar enderecos suspeitos
 * sem motivo, que e justamente o habito que a ferramenta desencoraja.
 */

"use client";

import { ArrowDown, ExternalLink, Loader2, Radio, TriangleAlert } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { SeverityBadge } from "@/components/SeverityBadge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { resolveUrl } from "@/services/api";
import type { UrlResolutionResult } from "@/types/analysis";

type State =
  | { status: "idle" }
  | { status: "resolving" }
  | { status: "done"; result: UrlResolutionResult }
  | { status: "failed"; message: string };

export function RedirectChain({ url }: { url: string }) {
  const t = useTranslations("redirect");
  const [state, setState] = useState<State>({ status: "idle" });

  async function resolve() {
    setState({ status: "resolving" });

    try {
      setState({ status: "done", result: await resolveUrl(url) });
    } catch (error) {
      setState({
        status: "failed",
        message: error instanceof Error ? error.message : t("failed"),
      });
    }
  }

  return (
    <Card className="fg-card">
      <CardContent className="flex flex-col gap-4">
        <div className="flex flex-col gap-1">
          <h3 className="flex items-center gap-2 text-sm font-medium">
            <span
              aria-hidden
              className="h-3.5 w-0.5 shrink-0 rounded-full"
              style={{ background: "var(--brand-magenta)" }}
            />
            {t("title")}
          </h3>
          <p className="text-xs leading-relaxed text-muted-foreground">{t("hint")}</p>
        </div>

        {state.status === "idle" && (
          <Button variant="outline" size="sm" onClick={resolve} className="self-start">
            <Radio className="size-3.5" />
            {t("action")}
          </Button>
        )}

        {state.status === "resolving" && (
          <p className="flex items-center gap-2 text-xs text-muted-foreground">
            <Loader2 className="size-3.5 animate-spin" />
            {t("resolving")}
          </p>
        )}

        {state.status === "failed" && (
          <Alert variant="destructive">
            <TriangleAlert />
            <AlertTitle>{t("failed")}</AlertTitle>
            <AlertDescription>{state.message}</AlertDescription>
          </Alert>
        )}

        {state.status === "done" && <Chain result={state.result} />}
      </CardContent>
    </Card>
  );
}

function Chain({ result }: { result: UrlResolutionResult }) {
  const t = useTranslations("redirect");

  return (
    <div className="flex flex-col gap-4">
      <ol className="flex flex-col gap-1">
        {result.hops.map((hop, index) => (
          <li key={index} className="flex flex-col gap-1">
            {index > 0 && (
              <ArrowDown aria-hidden className="size-3 shrink-0 text-muted-foreground/50" />
            )}

            <div className="fg-row flex flex-wrap items-center gap-x-3 gap-y-1 rounded px-2 py-1.5">
              <span className="font-mono text-[11px] text-muted-foreground tabular-nums">
                {String(index + 1).padStart(2, "0")}
              </span>

              <span className="min-w-0 flex-1 font-mono text-xs break-all">{hop.url}</span>

              {hop.status_code !== null && (
                <span className="font-mono text-[11px] text-muted-foreground tabular-nums">
                  {hop.status_code}
                </span>
              )}
            </div>
          </li>
        ))}
      </ol>

      {/*
        Cadeia interrompida. O motivo importa: `internal_address` nao e falha,
        e a protecao funcionando - alguem tentou mandar o servidor para a
        propria rede interna, e dizer so "nao consegui" esconderia isso.
      */}
      {!result.completed && (
        <Alert>
          <TriangleAlert />
          <AlertTitle>{t("incomplete")}</AlertTitle>
          <AlertDescription>
            {t.has(`reason.${result.stopped_reason}`)
              ? t(`reason.${result.stopped_reason}`)
              : t("reason.unknown")}
          </AlertDescription>
        </Alert>
      )}

      {result.completed && result.final_url && (
        <div className="flex flex-col gap-2 rounded-md border p-3">
          <p className="text-xs text-muted-foreground">{t("destination")}</p>

          <p className="flex items-start gap-2 font-mono text-xs break-all">
            <ExternalLink aria-hidden className="mt-0.5 size-3.5 shrink-0" />
            {result.final_url}
          </p>

          {/*
            O destino passou pela MESMA analise que uma URL colada receberia.
            Mostrar a nota dele e o ponto do recurso: o encurtador pontuava 25
            e o destino pode pontuar 85.
          */}
          {result.destination && (
            <div className="flex items-center gap-3 border-t pt-2">
              <span className="text-2xl leading-none font-semibold tabular-nums">
                {result.destination.risk.score}
              </span>
              <span className="text-xs text-muted-foreground">/ 100</span>
              <SeverityBadge tone={result.destination.risk.level} />
            </div>
          )}
        </div>
      )}

      <p className="text-[11px] leading-relaxed text-muted-foreground">
        {result.disclaimer}
      </p>
    </div>
  );
}
