/**
 * Etiqueta de severidade e de nivel de risco.
 *
 * Usa o Badge do shadcn como base, com uma camada de cor propria por cima.
 * As variantes que vem de fabrica sao semanticas da interface (primary,
 * destructive, outline) e nao cobrem uma escala de cinco niveis.
 *
 * As cores ORDENAM a atencao, mas nao gritam: o score e uma heuristica de
 * triagem, e uma tela alarmista contradiria o disclaimer que a propria API
 * devolve em toda resposta.
 */

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { RiskLevel, Severity } from "@/types/analysis";

const TONE_STYLES: Record<Severity | RiskLevel, string> = {
  info: "border-sky-500/30 bg-sky-500/10 text-sky-600 dark:text-sky-400",
  low: "border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
  medium: "border-amber-500/30 bg-amber-500/10 text-amber-600 dark:text-amber-400",
  high: "border-orange-500/30 bg-orange-500/10 text-orange-600 dark:text-orange-400",
  critical: "border-red-500/30 bg-red-500/10 text-red-600 dark:text-red-400",
};

/** Cor da barra de progresso do score, por faixa. */
export const RISK_BAR_COLORS: Record<RiskLevel, string> = {
  low: "bg-emerald-500",
  medium: "bg-amber-500",
  high: "bg-orange-500",
  critical: "bg-red-500",
};

interface SeverityBadgeProps {
  tone: Severity | RiskLevel;
  label?: string;
  className?: string;
}

export function SeverityBadge({ tone, label, className }: SeverityBadgeProps) {
  return (
    <Badge
      variant="outline"
      className={cn(
        "border font-mono text-[10px] tracking-wider uppercase",
        TONE_STYLES[tone],
        className,
      )}
    >
      {label ?? tone}
    </Badge>
  );
}
