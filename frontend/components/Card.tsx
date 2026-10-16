/**
 * Blocos de layout reaproveitados pelo relatorio inteiro.
 *
 * Extrair estas tres pecas economiza muita repeticao: praticamente todo painel
 * do relatorio e um Card com varias DataRow dentro. Quando o espacamento ou a
 * borda precisarem mudar, muda aqui e vale para todos.
 */

import type { ReactNode } from "react";

interface CardProps {
  title: string;
  /** Texto curto abaixo do titulo, para contextualizar o que o painel mostra. */
  hint?: string;
  children: ReactNode;
}

export function Card({ title, hint, children }: CardProps) {
  return (
    <section className="rounded-lg border border-zinc-200 p-4 dark:border-zinc-800">
      <h3 className="text-sm font-semibold">{title}</h3>
      {hint && <p className="mt-0.5 text-xs text-zinc-500 dark:text-zinc-400">{hint}</p>}
      <div className="mt-3">{children}</div>
    </section>
  );
}

interface DataRowProps {
  label: string;
  children: ReactNode;
  /**
   * Usa fonte monoespacada e permite quebra no meio da palavra.
   * Necessario para hashes e URLs, que nao tem espacos onde quebrar.
   */
  mono?: boolean;
}

export function DataRow({ label, children, mono = false }: DataRowProps) {
  return (
    <div className="flex flex-col gap-0.5 border-b border-zinc-100 py-2 last:border-0 sm:flex-row sm:gap-4 dark:border-zinc-900">
      <dt className="shrink-0 text-xs text-zinc-500 sm:w-44 dark:text-zinc-400">{label}</dt>
      <dd className={`min-w-0 break-words text-sm ${mono ? "font-mono text-xs break-all" : ""}`}>
        {children}
      </dd>
    </div>
  );
}

/** Marcador para valores ausentes - evita celula vazia sem explicacao. */
export function Empty({ children = "not present" }: { children?: ReactNode }) {
  return <span className="text-zinc-400 dark:text-zinc-600">{children}</span>;
}

/** Lista de rotulo e valor. Usa <dl> porque e exatamente o que ele descreve. */
export function DataList({ children }: { children: ReactNode }) {
  return <dl className="flex flex-col">{children}</dl>;
}
