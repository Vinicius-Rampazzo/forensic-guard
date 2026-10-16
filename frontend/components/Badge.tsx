/**
 * Etiqueta colorida de severidade e de nivel de risco.
 *
 * As cores seguem a filosofia do projeto: elas ORDENAM a atencao, mas nao
 * gritam. O score e uma heuristica de triagem, nao um veredito - uma tela
 * piscando vermelho contradiria o proprio disclaimer que a API devolve.
 */

import type { RiskLevel, Severity } from "@/types/analysis";

/**
 * Paleta por severidade.
 *
 * Cada entrada tem borda, fundo translucido e texto. O fundo com opacidade
 * funciona igual no tema claro e no escuro, o que evita manter duas paletas.
 */
const SEVERITY_STYLES: Record<Severity, string> = {
  info: "border-sky-500/40 bg-sky-500/10 text-sky-600 dark:text-sky-400",
  low: "border-emerald-500/40 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
  medium: "border-amber-500/40 bg-amber-500/10 text-amber-600 dark:text-amber-400",
  high: "border-orange-500/40 bg-orange-500/10 text-orange-600 dark:text-orange-400",
  critical: "border-red-500/40 bg-red-500/10 text-red-600 dark:text-red-400",
};

/** Niveis de risco reaproveitam as mesmas cores das severidades. */
const RISK_STYLES: Record<RiskLevel, string> = {
  low: SEVERITY_STYLES.low,
  medium: SEVERITY_STYLES.medium,
  high: SEVERITY_STYLES.high,
  critical: SEVERITY_STYLES.critical,
};

interface BadgeProps {
  label: string;
  tone: Severity | RiskLevel;
  className?: string;
}

export function Badge({ label, tone, className = "" }: BadgeProps) {
  const style = SEVERITY_STYLES[tone as Severity] ?? RISK_STYLES[tone as RiskLevel];

  return (
    <span
      className={`inline-flex items-center rounded border px-2 py-0.5 font-mono text-[11px] font-medium uppercase tracking-wider ${style} ${className}`}
    >
      {label}
    </span>
  );
}

export { RISK_STYLES, SEVERITY_STYLES };
