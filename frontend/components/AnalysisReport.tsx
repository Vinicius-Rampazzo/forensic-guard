/**
 * O relatorio completo de uma analise.
 *
 * Layout de painel: navegacao lateral com as secoes, cabecalho fixo mantendo
 * nome do arquivo e score sempre visiveis, e a secao selecionada ao lado.
 *
 * O cabecalho ser fixo e deliberado. Ao descer por 400 linhas de strings e
 * facil esquecer de qual arquivo se esta falando e que nota ele tirou - e e
 * justamente essa a informacao que da sentido a tudo o que esta abaixo.
 *
 * As secoes sao montadas a partir do que a resposta traz, nao de uma lista
 * fixa: um e-mail nao ganha secao de EXIF, uma imagem nao ganha secao de
 * anexos. Secao vazia e pior que secao ausente, porque sugere que algo faltou.
 */

"use client";

import {
  AlertTriangle,
  BarChart3,
  Download,
  Fingerprint,
  FileText,
  Image as ImageIcon,
  Link2,
  Mail,
  Paperclip,
  type LucideIcon,
  ScrollText,
} from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";

import { AnalysisCharts } from "@/components/AnalysisCharts";
import { AttachmentList } from "@/components/AttachmentList";
import { ExportPanel } from "@/components/ExportPanel";
import { EmailHeaders } from "@/components/EmailHeaders";
import { ExifCard } from "@/components/ExifCard";
import { FileOverview } from "@/components/FileOverview";
import { HashCard } from "@/components/HashCard";
import { IndicatorsList } from "@/components/IndicatorsList";
import { RiskSummary } from "@/components/RiskSummary";
import { StringsPanel } from "@/components/StringsPanel";
import { UrlList } from "@/components/UrlList";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { AnalysisResult } from "@/types/analysis";

interface Section {
  id: string;
  label: string;
  icon: LucideIcon;
  count?: number;
  /** Destaca a secao na navegacao quando ela contem algo que pede atencao. */
  alert?: boolean;
  content: React.ReactNode;
}

export function AnalysisReport({ result }: { result: AnalysisResult }) {
  const t = useTranslations("report");
  const sections = buildSections(result, t);
  const [activeId, setActiveId] = useState(sections[0].id);

  const active = sections.find((section) => section.id === activeId) ?? sections[0];

  const rootRef = useRef<HTMLDivElement>(null);
  const summaryRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const root = rootRef.current;
    const summary = summaryRef.current;

    if (!root || !summary) return;

    /*
      A navegacao lateral tambem gruda na rolagem, e precisa parar logo abaixo
      do resumo - nao atras dele. Mas a altura do resumo nao e fixa: o nome do
      arquivo quebra em mais linhas conforme o comprimento e a largura da
      janela.

      Entao ela e medida e publicada como variavel CSS, que a navegacao soma no
      `top` dela. ResizeObserver e nao estado do React: a altura e uma medida
      do layout, e devolve-la ao React so provocaria uma re-renderizacao para
      escrever de volta no mesmo DOM de onde ela veio.
    */
    const observer = new ResizeObserver(() => {
      root.style.setProperty("--fg-summary-height", `${summary.offsetHeight}px`);
    });

    observer.observe(summary);

    return () => observer.disconnect();
  }, []);

  return (
    <div ref={rootRef} className="flex flex-col gap-6">
      <RiskSummary
        ref={summaryRef}
        filename={result.filename}
        risk={result.risk}
        detection={result.detection}
        size={result.file.size}
        disclaimer={result.disclaimer}
      />

      <div className="grid gap-6 lg:grid-cols-[13rem_minmax(0,1fr)]">
        <SectionNav sections={sections} activeId={active.id} onSelect={setActiveId} />

        {/*
          `min-w-0` e indispensavel num filho de grid que contem texto sem
          espacos - hashes e URLs. Sem ele o conteudo empurra a coluna e a
          pagina inteira ganha rolagem horizontal.
        */}
        {/*
          A chave muda junto com a secao, entao o React recria o elemento e a
          animacao de entrada roda de novo a cada troca.
        */}
        <div key={active.id} className="fg-rise min-w-0">
          {active.content}
        </div>
      </div>
    </div>
  );
}

function SectionNav({
  sections,
  activeId,
  onSelect,
}: {
  sections: Section[];
  activeId: string;
  onSelect: (id: string) => void;
}) {
  return (
    // No celular vira uma fileira rolavel; a partir de lg, coluna fixa.
    <nav
      aria-label="Report sections"
      /*
        Gruda abaixo do resumo, nao atras dele.

        A conta e: a barra de cima, mais o respiro que o resumo deixa, mais a
        altura do proprio resumo, mais um respiro. `--fg-summary-height` e
        escrita pelo ResizeObserver la em cima; o `0px` de reserva vale para o
        primeiro quadro, antes da primeira medicao.
      */
      className="flex gap-1 overflow-x-auto border-b pb-2 lg:sticky lg:top-[calc(var(--app-header-height)+0.75rem+var(--fg-summary-height,0px)+1rem)] lg:h-fit lg:flex-col lg:overflow-visible lg:border-b-0 lg:pb-0"
    >
      {sections.map((section) => {
        const isActive = section.id === activeId;
        const Icon = section.icon;

        return (
          <Button
            key={section.id}
            variant="ghost"
            size="sm"
            aria-current={isActive ? "page" : undefined}
            onClick={() => onSelect(section.id)}
            className={cn(
              "group relative shrink-0 justify-start gap-2 font-normal transition-all duration-200 lg:w-full",
              isActive
                ? "bg-muted font-medium"
                : "hover:translate-x-0.5 hover:bg-muted/50",
            )}
          >
            {/*
              Barra ciano marcando a secao ativa. Ela cresce a partir do
              nada, entao a troca de secao tem movimento em vez de um salto.
            */}
            <span
              aria-hidden
              className={cn(
                "absolute left-0 w-0.5 rounded-full transition-all duration-200",
                isActive ? "h-5 opacity-100" : "h-0 opacity-0",
              )}
              style={{ background: "var(--brand-cyan)" }}
            />
            <Icon
              className={cn(
                "size-4 shrink-0 transition-colors duration-200",
                section.alert
                  ? "text-red-500"
                  : isActive
                    ? "text-[var(--brand-cyan)]"
                    : "text-muted-foreground",
              )}
            />
            <span className="truncate">{section.label}</span>
            {section.count !== undefined && (
              <span className="ml-auto font-mono text-[11px] text-muted-foreground tabular-nums">
                {section.count}
              </span>
            )}
          </Button>
        );
      })}
    </nav>
  );
}

/** Monta a lista de secoes para esta evidencia. */
type Translate = (key: string) => string;

function buildSections(result: AnalysisResult, t: Translate): Section[] {
  const scored = result.risk.indicators.filter((indicator) => indicator.score > 0);

  const sections: Section[] = [
    {
      // Primeiro de proposito: e a resposta a pergunta que o usuario tem -
      // "por que esta nota?". As demais secoes sao o detalhe que sustenta.
      id: "indicators",
      label: t("indicators"),
      icon: AlertTriangle,
      count: result.risk.indicators.length,
      alert: scored.length > 0,
      content: <IndicatorsList indicators={result.risk.indicators} />,
    },
    {
      id: "overview",
      label: t("overview"),
      icon: FileText,
      content: <FileOverview result={result} />,
    },
    {
      id: "hashes",
      label: t("hashes"),
      icon: Fingerprint,
      content: <HashCard hashes={result.file.hashes} />,
    },
  ];

  if (result.image) {
    sections.push({
      id: "image",
      label: t("image"),
      icon: ImageIcon,
      content: <ExifCard image={result.image} />,
    });
  }

  if (result.email) {
    const email = result.email;
    const misleading = email.links.filter((link) => link.misleading).length;
    const executables = email.attachments.filter(
      (attachment) =>
        attachment.analysis?.detection.detected_category === "executable",
    ).length;

    sections.push(
      {
        id: "email",
        label: t("headers"),
        icon: Mail,
        alert: email.reply_to_mismatch || email.return_path_mismatch,
        content: <EmailHeaders email={email} />,
      },
      {
        id: "links",
        label: t("links"),
        icon: Link2,
        count: email.links.length + email.urls.length,
        alert: misleading > 0,
        content: <UrlList links={email.links} urls={email.urls} />,
      },
      {
        id: "attachments",
        label: t("attachments"),
        icon: Paperclip,
        count: email.attachments.length,
        alert: executables > 0,
        content: (
          <AttachmentList
            attachments={email.attachments}
            truncated={email.attachments_truncated}
          />
        ),
      },
    );
  }

  sections.push(
    {
      id: "charts",
      label: t("charts"),
      icon: BarChart3,
      content: <AnalysisCharts result={result} />,
    },
    {
      id: "strings",
      label: t("strings"),
      icon: ScrollText,
      count: result.strings.total,
      content: <StringsPanel strings={result.strings} />,
    },
    {
      id: "export",
      label: t("export"),
      icon: Download,
      content: <ExportPanel result={result} />,
    },
  );

  return sections;
}
