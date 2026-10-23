/**
 * Visao geral da evidencia.
 *
 * Comeca com blocos de numero, nao com tabela. Tamanho, entropia, tipo e
 * contagem de indicadores sao os quatro dados que respondem "o que e isto?" -
 * e um numero grande responde isso mais rapido que uma linha de tabela.
 *
 * O detalhe fica abaixo, em lista de rotulo e valor, para quem quiser conferir.
 */

"use client";

import { Binary, FileType2, Gauge, ScrollText } from "lucide-react";
import { useTranslations } from "next-intl";
import type { ElementType } from "react";

import { Card, DataList, DataRow, Empty } from "@/components/Card";
import { describeEntropy, formatBytes, formatCount } from "@/components/format";
import { Card as ShadcnCard, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { AnalysisResult } from "@/types/analysis";

/** Acima deste valor a entropia sugere compressao, cifragem ou empacotamento. */
const HIGH_ENTROPY_THRESHOLD = 7.2;

export function FileOverview({ result }: { result: AnalysisResult }) {
  const t = useTranslations("overview");
  const { file, detection, strings, risk } = result;

  const scored = risk.indicators.filter((indicator) => indicator.score > 0).length;

  return (
    <div className="flex flex-col gap-4">
      <div className="fg-stagger grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <StatTile
          icon={Binary}
          label={t("size")}
          value={formatBytes(file.size)}
          detail={`${formatCount(file.size)} bytes`}
        />
        <StatTile
          icon={Gauge}
          label={t("entropy")}
          value={file.entropy.toFixed(2)}
          detail={describeEntropy(file.entropy)}
          alert={file.entropy > HIGH_ENTROPY_THRESHOLD}
        />
        <StatTile
          icon={FileType2}
          label={t("detected")}
          value={detection.detected_name ?? t("notRecognised")}
          detail={
            detection.confirmed_bytes > 0
              ? `${detection.confirmed_bytes} bytes · ${
                  detection.confirmed_bytes <= 2 ? t("weakSignature") : t("strongSignature")
                }`
              : undefined
          }
          small
        />
        <StatTile
          icon={ScrollText}
          label={t("indicators")}
          value={String(risk.indicators.length)}
          detail={`${scored} scored · ${formatCount(strings.total)} ${t("strings").toLowerCase()}`}
          alert={scored > 0}
        />
      </div>

      <Card
        title="Type detection"
        hint="What the file claims to be, compared with what its bytes say it is."
      >
        <DataList>
          <DataRow label="Declared extension" mono>
            {detection.declared_extension || <Empty>none</Empty>}
          </DataRow>

          <DataRow label="Detected MIME" mono>
            {detection.detected_mime ?? <Empty>—</Empty>}
          </DataRow>

          <DataRow label="Second opinion" mono>
            {detection.puremagic_mime ?? <Empty>no opinion</Empty>}
            {detection.second_opinion_agrees === false && (
              <span className="ml-2 font-sans text-amber-500">
                disagrees with the signature table
              </span>
            )}
          </DataRow>

          {detection.ambiguous_with.length > 0 && (
            <DataRow label="Also matched">{detection.ambiguous_with.join(", ")}</DataRow>
          )}

          <DataRow label="Evidence type" mono>
            {detection.evidence_type}
          </DataRow>
        </DataList>

        {detection.notes.length > 0 && (
          <ul className="mt-3 flex flex-col gap-1 border-t pt-3">
            {detection.notes.map((note) => (
              <li key={note} className="text-xs text-muted-foreground">
                {note}
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}

function StatTile({
  icon: Icon,
  label,
  value,
  detail,
  alert = false,
  small = false,
}: {
  icon: ElementType;
  label: string;
  value: string;
  detail?: string;
  alert?: boolean;
  small?: boolean;
}) {
  return (
    <ShadcnCard className="fg-card gap-0 py-4">
      <CardContent className="flex flex-col gap-1 px-4">
        <div className="flex items-center gap-1.5 text-muted-foreground">
          <Icon className="size-3.5" />
          <span className="text-[10px] tracking-wider uppercase">{label}</span>
        </div>

        <span
          className={cn(
            "truncate font-mono leading-tight font-semibold tabular-nums",
            small ? "text-sm" : "text-xl",
            alert && "text-amber-500",
          )}
        >
          {value}
        </span>

        {detail && (
          <span className="truncate text-[11px] text-muted-foreground">{detail}</span>
        )}
      </CardContent>
    </ShadcnCard>
  );
}
