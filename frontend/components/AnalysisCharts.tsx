/**
 * Visualizacoes da analise.
 *
 * Quatro graficos, cada um respondendo a uma pergunta que uma tabela responde
 * mal:
 *
 * 1. **Mapa de entropia** - ONDE no arquivo o conteudo muda de natureza. A
 *    entropia global de um executavel empacotado fica em torno de 6,5, a media
 *    entre o codigo normal e a secao comprimida. O mapa mostra o planalto que
 *    a media esconde.
 * 2. **Composicao da pontuacao** - quanto cada regra pesou no total.
 * 3. **Distribuicao por severidade** - a proporcao entre achados graves e
 *    informativos, com o total no centro.
 * 4. **Artefatos por categoria** - quantos de cada padrao foram reconhecidos.
 *
 * Cores
 * -----
 * Duas paletas com papeis diferentes, e elas nao se misturam:
 *
 * - **severidade** e uma paleta de ESTADO (info a critico). Reservada, nunca
 *   reaproveitada para "mais uma serie", e sempre acompanhada do rotulo em
 *   texto - cor sozinha nao comunica para quem nao a distingue.
 * - **categorica** identifica categorias sem ordem entre si. Vem das
 *   variaveis `--chart-1` a `--chart-6`, derivadas das cores da logo e
 *   validadas para contraste e para tres tipos de daltonismo.
 */

"use client";

import { useTranslations } from "next-intl";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  Pie,
  PieChart,
  ReferenceArea,
  ReferenceLine,
  XAxis,
  YAxis,
} from "recharts";

import { Card } from "@/components/Card";
import { formatCount } from "@/components/format";
import {
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";
import type { AnalysisResult, Artifacts, Severity } from "@/types/analysis";

/**
 * Paleta de ESTADO. Reservada a severidade e a mais nada.
 *
 * Valores literais porque o Recharts desenha em SVG e nao resolve classes do
 * Tailwind - ele precisa da cor final.
 */
const SEVERITY_COLORS: Record<Severity, string> = {
  info: "#38bdf8",
  low: "#34d399",
  medium: "#fbbf24",
  high: "#fb923c",
  critical: "#f87171",
};

const SEVERITY_ORDER: Severity[] = ["critical", "high", "medium", "low", "info"];

/** Acima deste valor a entropia sugere compressao, cifragem ou empacotamento. */
const HIGH_ENTROPY_THRESHOLD = 7.2;

export function AnalysisCharts({ result }: { result: AnalysisResult }) {
  return (
    <div className="flex flex-col gap-4">
      <EntropyMap blocks={result.file.entropy_blocks} overall={result.file.entropy} />

      <div className="grid gap-4 xl:grid-cols-2">
        <SeverityDonut result={result} />
        <ArtifactBreakdown artifacts={result.strings.artifacts} />
      </div>

      <ScoreComposition result={result} />
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* Mapa de entropia                                                           */
/* -------------------------------------------------------------------------- */

function EntropyMap({ blocks, overall }: { blocks: number[]; overall: number }) {
  const t = useTranslations("charts");

  if (blocks.length < 2) {
    return <EmptyChart title={t("entropyMap")} hint={t("entropyMapHint")} />;
  }

  const data = blocks.map((entropy, index) => ({
    // Posicao em porcentagem do arquivo: o numero do bloco nao diz nada a quem
    // le, mas "aos 60% do arquivo" diz.
    position: Math.round((index / (blocks.length - 1)) * 100),
    entropy,
  }));

  const peak = Math.max(...blocks);
  const suspicious = blocks.filter((value) => value > HIGH_ENTROPY_THRESHOLD).length;

  const config = {
    entropy: { label: t("entropyAxis"), color: "var(--chart-3)" },
  } satisfies ChartConfig;

  return (
    <Card
      title={t("entropyMap")}
      hint={t("entropyMapHint")}
      action={
        <div className="flex gap-4 text-right">
          <Stat label={t("peak")} value={peak.toFixed(2)} />
          <Stat label={t("average")} value={overall.toFixed(2)} />
          <Stat
            label={t("aboveThreshold")}
            value={`${Math.round((suspicious / blocks.length) * 100)}%`}
            alert={suspicious > 0}
          />
        </div>
      }
    >
      <ChartContainer config={config} className="h-64 w-full">
        <AreaChart data={data} margin={{ left: -18, right: 10, top: 10, bottom: 0 }}>
          <defs>
            <linearGradient id="fg-entropy-fill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--color-entropy)" stopOpacity={0.5} />
              <stop offset="100%" stopColor="var(--color-entropy)" stopOpacity={0.02} />
            </linearGradient>
          </defs>

          {/*
            Faixa de fundo marcando a zona de entropia alta. Comunica o
            significado antes de o leitor precisar interpretar a linha
            tracejada.
          */}
          <ReferenceArea
            y1={HIGH_ENTROPY_THRESHOLD}
            y2={8}
            fill={SEVERITY_COLORS.medium}
            fillOpacity={0.07}
          />

          <CartesianGrid vertical={false} strokeOpacity={0.25} />

          <XAxis
            dataKey="position"
            tickLine={false}
            axisLine={false}
            tickMargin={8}
            tickFormatter={(value) => `${value}%`}
            className="font-mono text-[10px]"
          />
          <YAxis
            domain={[0, 8]}
            ticks={[0, 2, 4, 6, 8]}
            tickLine={false}
            axisLine={false}
            width={34}
            className="font-mono text-[10px]"
          />

          <ReferenceLine
            y={HIGH_ENTROPY_THRESHOLD}
            strokeDasharray="4 4"
            stroke={SEVERITY_COLORS.medium}
            strokeOpacity={0.8}
            label={{
              value: `${HIGH_ENTROPY_THRESHOLD}`,
              position: "right",
              fontSize: 10,
              fill: SEVERITY_COLORS.medium,
            }}
          />

          <ChartTooltip
            cursor={{ strokeOpacity: 0.3 }}
            content={
              <ChartTooltipContent
                labelFormatter={(value) => `${value}% ${t("positionAxis")}`}
              />
            }
          />

          <Area
            dataKey="entropy"
            type="monotone"
            stroke="var(--color-entropy)"
            strokeWidth={2}
            fill="url(#fg-entropy-fill)"
            isAnimationActive={false}
            activeDot={{ r: 4, strokeWidth: 2 }}
          />
        </AreaChart>
      </ChartContainer>
    </Card>
  );
}

/* -------------------------------------------------------------------------- */
/* Distribuicao por severidade                                                */
/* -------------------------------------------------------------------------- */

function SeverityDonut({ result }: { result: AnalysisResult }) {
  const t = useTranslations("charts");
  const tRisk = useTranslations("risk");

  const counts = SEVERITY_ORDER.map((severity) => ({
    severity,
    label: tRisk(severity),
    count: result.risk.indicators.filter((item) => item.severity === severity).length,
  })).filter((entry) => entry.count > 0);

  if (counts.length === 0) {
    return <EmptyChart title={t("severity")} hint={t("severityHint")} />;
  }

  const config = Object.fromEntries(
    counts.map((entry) => [entry.severity, { label: entry.label, color: SEVERITY_COLORS[entry.severity] }]),
  ) satisfies ChartConfig;

  const total = counts.reduce((sum, entry) => sum + entry.count, 0);

  return (
    <Card title={t("severity")} hint={t("severityHint")}>
      <ChartContainer config={config} className="mx-auto h-56 w-full">
        <PieChart>
          <ChartTooltip content={<ChartTooltipContent nameKey="severity" hideLabel />} />
          <Pie
            data={counts}
            dataKey="count"
            nameKey="severity"
            innerRadius={52}
            outerRadius={78}
            // Separacao de 2px entre fatias: sem ela, duas cores adjacentes
            // se tocam e a fronteira some para quem nao as distingue.
            paddingAngle={2}
            strokeWidth={2}
            stroke="var(--card)"
            isAnimationActive={false}
          >
            {counts.map((entry) => (
              <Cell key={entry.severity} fill={SEVERITY_COLORS[entry.severity]} />
            ))}
          </Pie>

          {/* Legenda sempre presente: identidade nunca so pela cor. */}
          <ChartLegend content={<ChartLegendContent nameKey="severity" />} />
        </PieChart>
      </ChartContainer>

      {/*
        O total vai abaixo do grafico, nao sobreposto ao centro. Texto dentro
        da rosca concorre com as fatias e quebra em telas estreitas.
      */}
      <p className="mt-1 text-center text-xs text-muted-foreground">
        {t("totalIndicators", { count: total })}
      </p>
    </Card>
  );
}

/* -------------------------------------------------------------------------- */
/* Artefatos por categoria                                                    */
/* -------------------------------------------------------------------------- */

const ARTIFACT_LABELS: Record<keyof Artifacts, string> = {
  urls: "URLs",
  ipv4: "IPv4",
  ipv6: "IPv6",
  emails: "Emails",
  windows_paths: "Paths",
  suspicious_keywords: "Commands",
};

function ArtifactBreakdown({ artifacts }: { artifacts: Artifacts }) {
  const t = useTranslations("charts");

  const data = (Object.entries(artifacts) as [keyof Artifacts, string[]][])
    .filter(([, values]) => Array.isArray(values) && values.length > 0)
    .map(([category, values], index) => ({
      category: ARTIFACT_LABELS[category],
      count: values.length,
      // Cor por entidade, atribuida na ordem fixa da paleta. Nunca ciclada e
      // nunca dependente da posicao no ranking - se a ordem mudar, cada
      // categoria mantem a sua cor.
      fill: `var(--chart-${(index % 6) + 1})`,
    }));

  if (data.length === 0) {
    return <EmptyChart title={t("artifacts")} hint={t("artifactsHint")} />;
  }

  const config = { count: { label: t("found") } } satisfies ChartConfig;

  return (
    <Card title={t("artifacts")} hint={t("artifactsHint")}>
      <ChartContainer
        config={config}
        style={{ height: `${Math.max(140, data.length * 36 + 24)}px` }}
        className="w-full"
      >
        <BarChart data={data} layout="vertical" margin={{ left: 4, right: 36 }}>
          <XAxis type="number" hide />
          <YAxis
            type="category"
            dataKey="category"
            width={78}
            tickLine={false}
            axisLine={false}
            className="font-mono text-[10px]"
          />
          <ChartTooltip cursor={false} content={<ChartTooltipContent hideLabel />} />
          <Bar dataKey="count" radius={4} barSize={18} isAnimationActive={false}>
            {data.map((entry) => (
              <Cell key={entry.category} fill={entry.fill} />
            ))}
            {/*
              Rotulo direto na ponta da barra. Com poucas categorias ele
              substitui o eixo de valores - menos elementos, leitura
              imediata, e o numero fica legivel sem depender da cor.
            */}
            <LabelList
              dataKey="count"
              position="right"
              offset={8}
              className="fill-muted-foreground font-mono text-[10px]"
            />
          </Bar>
        </BarChart>
      </ChartContainer>
    </Card>
  );
}

/* -------------------------------------------------------------------------- */
/* Composicao da pontuacao                                                    */
/* -------------------------------------------------------------------------- */

function ScoreComposition({ result }: { result: AnalysisResult }) {
  const t = useTranslations("charts");

  const scored = result.risk.indicators.filter((indicator) => indicator.score > 0);

  if (scored.length === 0) {
    return <EmptyChart title={t("scoreComposition")} hint={t("scoreCompositionHint")} />;
  }

  const data = scored.map((indicator) => ({
    // O id e mais curto que o titulo e cabe no eixo sem quebrar; o titulo
    // completo aparece no tooltip.
    name: indicator.id.split(".")[1] ?? indicator.id,
    score: indicator.score,
    severity: indicator.severity,
    title: indicator.title,
  }));

  const total = data.reduce((sum, entry) => sum + entry.score, 0);

  const config = { score: { label: t("points") } } satisfies ChartConfig;

  return (
    <Card
      title={t("scoreComposition")}
      hint={t("scoreCompositionHint")}
      action={
        <Stat
          label={t("sum")}
          value={total > 100 ? `${total} → 100` : String(total)}
          alert={total >= 76}
        />
      }
    >
      <ChartContainer
        config={config}
        // Altura proporcional ao numero de barras: altura fixa comprime as
        // barras ate ficarem ilegiveis quando ha muitos indicadores.
        style={{ height: `${Math.max(140, data.length * 36 + 24)}px` }}
        className="w-full"
      >
        <BarChart data={data} layout="vertical" margin={{ left: 4, right: 40 }}>
          <XAxis type="number" hide domain={[0, Math.max(...data.map((d) => d.score))]} />
          <YAxis
            type="category"
            dataKey="name"
            width={150}
            tickLine={false}
            axisLine={false}
            className="font-mono text-[10px]"
          />
          <ChartTooltip
            cursor={false}
            content={
              <ChartTooltipContent
                labelFormatter={(_, payload) =>
                  (payload?.[0]?.payload as { title?: string })?.title ?? ""
                }
              />
            }
          />
          <Bar dataKey="score" radius={4} barSize={18} isAnimationActive={false}>
            {data.map((entry) => (
              <Cell key={entry.name} fill={SEVERITY_COLORS[entry.severity]} />
            ))}
            <LabelList
              dataKey="score"
              position="right"
              offset={8}
              // O tipo do Recharts aceita texto ou numero, entao o valor
              // chega como `unknown` do ponto de vista do TypeScript.
              formatter={(value: unknown) => `+${value}`}
              className="fill-muted-foreground font-mono text-[10px]"
            />
          </Bar>
        </BarChart>
      </ChartContainer>
    </Card>
  );
}

/* -------------------------------------------------------------------------- */
/* Pecas compartilhadas                                                       */
/* -------------------------------------------------------------------------- */

function Stat({
  label,
  value,
  alert = false,
}: {
  label: string;
  value: string;
  alert?: boolean;
}) {
  return (
    <div className="flex flex-col items-end">
      {/*
        O valor usa cor de texto, nunca a cor da serie. Numero colorido
        compete com as marcas do grafico e confunde quem procura a relacao
        entre eles.
      */}
      <span
        className={`font-mono text-sm leading-none font-medium tabular-nums ${
          alert ? "text-amber-500" : ""
        }`}
      >
        {value}
      </span>
      <span className="text-[10px] tracking-wide text-muted-foreground uppercase">
        {label}
      </span>
    </div>
  );
}

function EmptyChart({ title, hint }: { title: string; hint: string }) {
  const t = useTranslations("charts");

  return (
    <Card title={title} hint={hint}>
      <p className="py-6 text-center text-sm text-muted-foreground">{t("noData")}</p>
    </Card>
  );
}

export { formatCount };
