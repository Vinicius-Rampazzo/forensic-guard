/**
 * Estado de espera durante a analise.
 *
 * Duas coisas acontecem aqui ao mesmo tempo:
 *
 * - a marca com a linha de varredura animada, que da identidade ao momento e
 *   sugere o que esta acontecendo - um arquivo sendo percorrido;
 * - o esqueleto do relatorio que vai chegar.
 *
 * O esqueleto nao e enfeite: ele comunica a FORMA do resultado, entao quando
 * o conteudo chega ele ocupa o espaco que ja estava reservado, sem o salto
 * visual que um indicador centralizado provoca.
 *
 * As etapas listadas sao as que o backend realmente executa, na ordem em que
 * executa. Nao ha progresso real vindo do servidor - a API responde de uma
 * vez - entao elas informam o QUE esta sendo feito, nunca quanto falta.
 */

"use client";

import { useTranslations } from "next-intl";

import { Logo } from "@/components/Logo";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

const STEPS = ["hashes", "entropy", "signature", "strings", "indicators"];

export function AnalysisLoading({ filename }: { filename: string }) {
  const t = useTranslations("upload");

  return (
    <div className="fg-rise flex flex-col gap-6">
      <Card className="overflow-hidden">
        {/*
          Faixa de varredura atravessando o topo do cartao. `overflow-hidden`
          no cartao e o que a mantem dentro da borda arredondada.
        */}
        <div className="relative -mt-6 h-0.5 w-full overflow-hidden bg-muted">
          {/* Varredura nas duas cores da marca, atravessando da esquerda para
              a direita como se percorresse o arquivo. */}
          <div
            className="fg-sweep h-full w-1/3"
            style={{
              background:
                "linear-gradient(90deg, transparent, var(--brand-magenta), var(--brand-cyan), transparent)",
            }}
          />
        </div>

        <CardContent className="flex flex-col items-center gap-5 py-6 text-center">
          <Logo animated glow className="size-20" />

          <div className="flex min-w-0 max-w-full flex-col gap-1">
            {/*
              aria-live avisa o leitor de tela quando este texto aparece, sem
              roubar o foco de onde o usuario estava.
            */}
            <p className="text-sm font-medium" aria-live="polite">
              {t("analysing")}
            </p>
            <p className="min-w-0 truncate font-mono text-xs text-muted-foreground">
              {filename}
            </p>
          </div>

          <ul className="flex flex-wrap items-center justify-center gap-x-3 gap-y-1">
            {STEPS.map((step, index) => (
              <li
                key={step}
                className="font-mono text-[10px] tracking-wider text-muted-foreground uppercase"
                // Cada etapa pisca com um atraso diferente, dando a impressao
                // de uma sequencia sendo percorrida.
                style={{
                  animation: `pulse 1.6s ease-in-out ${index * 0.22}s infinite`,
                }}
              >
                {step}
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-[13rem_minmax(0,1fr)]">
        <div className="flex gap-1 lg:flex-col">
          {[0, 1, 2, 3].map((index) => (
            <Skeleton key={index} className="h-8 w-28 lg:w-full" />
          ))}
        </div>

        <div className="flex min-w-0 flex-col gap-3">
          <Skeleton className="h-28 w-full" />
          <Skeleton className="h-28 w-full" />
          <Skeleton className="h-28 w-full" />
        </div>
      </div>
    </div>
  );
}
