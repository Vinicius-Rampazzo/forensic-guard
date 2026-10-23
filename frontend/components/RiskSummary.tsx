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

"use client";

import type { Ref } from "react";

import { RISK_BAR_COLORS, SeverityBadge } from "@/components/SeverityBadge";
import { ScrambleText } from "@/components/ScrambleText";
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
  /**
   * O relatorio precisa medir a altura deste cartao para grudar a navegacao
   * lateral logo abaixo dele.
   *
   * A referencia vem de fora em vez de o cartao se envolver numa div propria
   * porque `position: sticky` so funciona dentro dos limites do pai. Um
   * involucro do tamanho exato do cartao daria a ele zero espaco para
   * deslizar, e o grude pararia de funcionar.
   */
  ref?: Ref<HTMLDivElement>;
}

export function RiskSummary({
  filename,
  risk,
  detection,
  size,
  disclaimer,
  ref,
}: RiskSummaryProps) {
  const scored = risk.indicators.filter((indicator) => indicator.score > 0).length;
  const informational = risk.indicators.length - scored;

  return (
    // `top` precisa cair ABAIXO da barra de cima, que tambem gruda e e mais
    // alta. Com um valor menor que ela, este cartao trava escondido atras do
    // cabecalho - era o que acontecia com `top-4`: o nome do arquivo e a nota
    // ficavam cortados justamente quando passavam a ser a unica referencia.
    //
    // O fundo e solido, e nao translucido como era antes. Com `bg-card/85` o
    // conteudo que rolava por baixo aparecia atraves do cartao, e um relatorio
    // forense com dois textos sobrepostos nao da para ler.
    <Card
      ref={ref}
      className="fg-card sticky top-[calc(var(--app-header-height)+0.75rem)] z-10 bg-card"
    >
      <CardContent className="flex flex-col gap-4">
        <div className="flex flex-wrap items-start justify-between gap-x-6 gap-y-3">
          <div className="flex min-w-0 flex-col gap-1">
            <h2 className="flex min-w-0 items-center gap-2 font-mono text-sm break-all">
              <span
                aria-hidden
                className="h-3.5 w-0.5 shrink-0 rounded-full"
                style={{ background: "var(--brand-cyan)" }}
              />
              {/*
                O nome do arquivo se decodifica, mas a pontuacao e os numeros
                abaixo nao. A diferenca importa: o nome e o ASSUNTO da analise,
                algo que quem enviou ja conhece. Pontuacao, hash e tamanho sao
                ACHADOS - ve-los piscar como outro valor antes de assentar
                seria a ferramenta brincando justamente com o que ela existe
                para afirmar.
              */}
              <ScrambleText text={filename} />
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
