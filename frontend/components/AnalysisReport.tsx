/**
 * O relatorio completo de uma analise.
 *
 * As abas mudam conforme o tipo de evidencia: um e-mail nao tem aba de EXIF,
 * uma imagem nao tem aba de anexos. A lista e montada a partir do que a
 * resposta realmente traz, e nao de uma estrutura fixa com secoes vazias.
 */

"use client";

import { useState } from "react";

import { AttachmentList } from "@/components/AttachmentList";
import { EmailHeaders } from "@/components/EmailHeaders";
import { ExifCard } from "@/components/ExifCard";
import { FileOverview } from "@/components/FileOverview";
import { HashCard } from "@/components/HashCard";
import { IndicatorsList } from "@/components/IndicatorsList";
import { RiskScore } from "@/components/RiskScore";
import { StringsPanel } from "@/components/StringsPanel";
import { Tabs, type Tab } from "@/components/Tabs";
import { UrlList } from "@/components/UrlList";
import type { AnalysisResult } from "@/types/analysis";

export function AnalysisReport({ result }: { result: AnalysisResult }) {
  const tabs = buildTabs(result);
  const [activeId, setActiveId] = useState(tabs[0].id);

  return (
    <div className="flex flex-col gap-6">
      <RiskScore
        filename={result.filename}
        risk={result.risk}
        disclaimer={result.disclaimer}
      />

      <Tabs tabs={tabs} activeId={activeId} onSelect={setActiveId} />
    </div>
  );
}

/**
 * Monta a lista de abas para esta evidencia.
 *
 * A aba de indicadores vem primeiro de proposito: e a resposta a pergunta que
 * o usuario realmente tem - "por que esta nota?". As demais sao o detalhe que
 * sustenta a resposta.
 */
function buildTabs(result: AnalysisResult): Tab[] {
  const tabs: Tab[] = [
    {
      id: "indicators",
      label: `Indicators (${result.risk.indicators.length})`,
      content: <IndicatorsList indicators={result.risk.indicators} />,
    },
    {
      id: "overview",
      label: "Overview",
      content: <FileOverview file={result.file} detection={result.detection} />,
    },
    {
      id: "hashes",
      label: "Hashes",
      content: <HashCard hashes={result.file.hashes} />,
    },
  ];

  if (result.image) {
    tabs.push({
      id: "image",
      label: "Image",
      content: <ExifCard image={result.image} />,
    });
  }

  if (result.email) {
    const email = result.email;

    tabs.push(
      {
        id: "email",
        label: "Headers",
        content: <EmailHeaders email={email} />,
      },
      {
        id: "links",
        label: `Links (${email.links.length + email.urls.length})`,
        content: <UrlList links={email.links} urls={email.urls} />,
      },
      {
        id: "attachments",
        label: `Attachments (${email.attachments.length})`,
        content: (
          <AttachmentList
            attachments={email.attachments}
            truncated={email.attachments_truncated}
          />
        ),
      },
    );
  }

  tabs.push({
    id: "strings",
    label: "Strings",
    content: <StringsPanel strings={result.strings} />,
  });

  return tabs;
}
