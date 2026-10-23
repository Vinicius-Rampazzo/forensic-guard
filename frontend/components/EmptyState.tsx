/**
 * Tela de upload: o que a ferramenta faz, antes de alguem usar.
 *
 * A versao anterior tinha apenas um retangulo tracejado escrito "Drop evidence
 * here". Quem chegava nao fazia ideia do que receberia de volta.
 *
 * Tres coisas precisam estar respondidas aqui:
 *   1. o que acontece com o arquivo que eu soltar
 *   2. o que eu recebo de volta
 *   3. o que acontece com a minha evidencia depois
 */

"use client";

import { FileSearch, FileUp, Image as ImageIcon, Link2, Mail, ShieldCheck } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { FileDropzone } from "@/components/FileDropzone";
import { UrlInput } from "@/components/UrlInput";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import type { RiskLevel } from "@/types/analysis";

/** O que cada tipo de evidencia produz. Os itens vem das traducoes. */
const CAPABILITIES = [
  { icon: FileSearch, key: "file", accent: "var(--brand-magenta)" },
  { icon: ImageIcon, key: "image", accent: "var(--brand-cyan)" },
  { icon: Mail, key: "email", accent: "var(--brand-magenta)" },
] as const;

const PRIVACY_POINTS = ["local", "noExecution", "temporary", "noHistory"] as const;

/** A escala de risco, para o numero depois fazer sentido. */
const RISK_SCALE: { range: string; level: RiskLevel; color: string }[] = [
  { range: "0 – 20", level: "low", color: "bg-emerald-500" },
  { range: "21 – 50", level: "medium", color: "bg-amber-500" },
  { range: "51 – 75", level: "high", color: "bg-orange-500" },
  { range: "76 – 100", level: "critical", color: "bg-red-500" },
];

interface EmptyStateProps {
  onFileSelected: (file: File) => void;
  onUrlSubmitted: (url: string) => void;
  disabled?: boolean;
  uploadLimit: number | null;
}

/** Qual tipo de evidencia o usuario esta entregando. */
type InputMode = "file" | "url";

export function EmptyState({
  onFileSelected,
  onUrlSubmitted,
  disabled,
  uploadLimit,
}: EmptyStateProps) {
  const [mode, setMode] = useState<InputMode>("file");
  const t = useTranslations("upload");
  const tUrl = useTranslations("url");
  const tCapabilities = useTranslations("capabilities");
  const tRisk = useTranslations("risk");
  const tPrivacy = useTranslations("privacy");
  const tApp = useTranslations("app");

  return (
    <div className="fg-rise flex flex-col gap-10">
      <section className="flex flex-col items-center gap-3 text-center">
        <h2 className="text-2xl font-semibold tracking-tight text-balance sm:text-3xl">
          {t("question")}
        </h2>
        <p className="max-w-2xl text-sm text-balance text-muted-foreground">
          {t("intro")}
        </p>
      </section>

      <div className="flex flex-col gap-4">
        {/*
          Abas como um grupo de botoes com role="tablist". Nao e enfeite de
          acessibilidade: sem isso um leitor de tela anuncia dois botoes
          soltos, sem dizer que formam um conjunto nem qual esta ativo.
        */}
        <div
          role="tablist"
          aria-label={tUrl("inputMode")}
          className="mx-auto flex gap-1 rounded-lg border p-1"
        >
          {(
            [
              { id: "file" as const, icon: FileUp, label: tUrl("fileTab") },
              { id: "url" as const, icon: Link2, label: tUrl("urlTab") },
            ]
          ).map(({ id, icon: Icon, label }) => (
            <Button
              key={id}
              role="tab"
              aria-selected={mode === id}
              variant="ghost"
              size="sm"
              onClick={() => setMode(id)}
              className={cn(
                "gap-2 transition-all duration-200",
                mode === id && "bg-muted font-medium",
              )}
            >
              <Icon
                className="size-4"
                style={mode === id ? { color: "var(--brand-cyan)" } : undefined}
              />
              {label}
            </Button>
          ))}
        </div>

        {/*
          A chave muda junto com o modo, entao o React recria o elemento e a
          animacao de entrada roda a cada troca de aba.
        */}
        <div key={mode} className="fg-rise">
          {mode === "file" ? (
            <FileDropzone
              onFileSelected={onFileSelected}
              disabled={disabled}
              uploadLimit={uploadLimit}
            />
          ) : (
            <UrlInput onSubmit={onUrlSubmitted} disabled={disabled} />
          )}
        </div>
      </div>

      <section className="fg-stagger grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {CAPABILITIES.map(({ icon: Icon, key, accent }) => (
          <Card key={key} className="fg-card">
            <CardContent className="flex flex-col gap-3">
              <div className="flex items-center gap-2">
                <Icon className="size-4" style={{ color: accent }} />
                <h3 className="text-sm font-medium">{tCapabilities(key)}</h3>
              </div>
              <ul className="flex flex-col gap-1.5">
                {/*
                  As listas vem como uma string separada por barras. Guardar um
                  array por idioma no JSON seria mais natural, mas o next-intl
                  trata arrays como objetos indexados e o acesso fica
                  desconfortavel - a barra resolve com uma linha.
                */}
                {tCapabilities(`${key}Items`)
                  .split("|")
                  .map((item) => (
                    <li key={item} className="text-xs text-muted-foreground">
                      {item}
                    </li>
                  ))}
              </ul>
            </CardContent>
          </Card>
        ))}
      </section>

      <section className="fg-stagger grid gap-4 lg:grid-cols-2">
        <Card className="fg-card">
          <CardContent className="flex flex-col gap-3">
            <h3 className="text-sm font-medium">{tRisk("title")}</h3>
            <p className="text-xs text-muted-foreground">{tRisk("explanation")}</p>

            <div className="mt-1 flex flex-col gap-1.5">
              {RISK_SCALE.map(({ range, level, color }) => (
                <div key={level} className="flex items-center gap-3">
                  <span className={`h-1.5 w-10 rounded-full ${color}`} />
                  <span className="font-mono text-[11px] text-muted-foreground tabular-nums">
                    {range}
                  </span>
                  <span className="font-mono text-[11px] tracking-wider uppercase">
                    {tRisk(level)}
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="fg-card">
          <CardContent className="flex flex-col gap-3">
            <div className="flex items-center gap-2">
              <ShieldCheck className="size-4 text-emerald-500" />
              <h3 className="text-sm font-medium">{tPrivacy("title")}</h3>
            </div>

            <ul className="flex flex-col gap-2 text-xs text-muted-foreground">
              {PRIVACY_POINTS.map((point) => (
                <li key={point}>{tPrivacy(point)}</li>
              ))}
            </ul>

            <Separator className="my-1" />

            <p className="text-[11px] text-muted-foreground">
              {tApp("disclaimerLine")}
            </p>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
