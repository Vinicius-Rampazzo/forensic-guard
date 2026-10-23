/**
 * Blocos de layout reaproveitados pelo relatorio inteiro.
 *
 * Sao uma camada fina por cima do Card do shadcn. O ganho de manter esta
 * camada, em vez de usar o shadcn direto em todo lugar, e que praticamente
 * todo painel do relatorio tem a mesma forma - titulo, uma linha de contexto,
 * e uma lista de rotulo/valor. Escrever isso uma vez evita repetir cinco
 * elementos em onze arquivos.
 *
 * E e esse ganho que permite a decodificacao do titulo entrar em TODO painel
 * do relatorio mexendo num arquivo so.
 *
 * O que NAO se decodifica
 * -----------------------
 * Rotulo embaralha; valor nao. Um hash, um tamanho ou uma pontuacao piscando
 * como outro numero antes de assentar - mesmo por meio segundo - e uma
 * ferramenta de pericia mentindo de brincadeira. O efeito fica restrito ao
 * texto que descreve o dado, nunca ao dado.
 */

"use client";

import type { ReactNode } from "react";

import { ScrambleText } from "@/components/ScrambleText";
import {
  Card as ShadcnCard,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface SectionCardProps {
  title: string;
  /** Texto curto abaixo do titulo, para contextualizar o painel. */
  hint?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
}

export function Card({ title, hint, action, children }: SectionCardProps) {
  return (
    <ShadcnCard className="fg-card">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-sm font-medium">
          {/*
            Barra magenta antes do titulo. E o acento da marca aplicado onde
            ele ajuda - marca o inicio de cada bloco sem colorir o texto, que
            precisa continuar legivel.
          */}
          <span
            aria-hidden
            className="h-3.5 w-0.5 shrink-0 rounded-full"
            style={{ background: "var(--brand-magenta)" }}
          />
          <ScrambleText text={title} />
        </CardTitle>
        {hint && <CardDescription className="text-xs">{hint}</CardDescription>}
        {action}
      </CardHeader>
      <CardContent>{children}</CardContent>
    </ShadcnCard>
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
    <div className="fg-row -mx-2 flex flex-col gap-0.5 rounded border-b px-2 py-2 last:border-0 sm:flex-row sm:gap-4">
      <dt className="shrink-0 text-xs text-muted-foreground sm:w-44">{label}</dt>
      <dd className={cn("min-w-0 text-sm break-words", mono && "font-mono text-xs break-all")}>
        {children}
      </dd>
    </div>
  );
}

/** Marcador para valores ausentes - evita celula vazia sem explicacao. */
export function Empty({ children = "not present" }: { children?: ReactNode }) {
  return <span className="text-muted-foreground/50">{children}</span>;
}

/** Lista de rotulo e valor. Usa <dl> porque e exatamente o que ele descreve. */
export function DataList({ children }: { children: ReactNode }) {
  return <dl className="flex flex-col">{children}</dl>;
}
