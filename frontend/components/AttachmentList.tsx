/**
 * Anexos da mensagem, cada um com a sua propria analise.
 *
 * Cada anexo passou pelo mesmo pipeline do arquivo principal e tem Risk Score
 * proprio. O caso que esta tela existe para mostrar: um `fatura.pdf` cujos
 * bytes comecam com `MZ` - declarado como PDF, detectado como executavel.
 */

import { Badge } from "@/components/Badge";
import { Card } from "@/components/Card";
import { formatBytes } from "@/components/FileOverview";
import type { Attachment } from "@/types/analysis";

interface AttachmentListProps {
  attachments: Attachment[];
  truncated: boolean;
}

export function AttachmentList({ attachments, truncated }: AttachmentListProps) {
  return (
    <Card
      title="Attachments"
      hint={
        truncated
          ? "A safety limit stopped the extraction — this listing is partial."
          : "Each attachment goes through the same analysis as the main evidence."
      }
    >
      {attachments.length === 0 ? (
        <p className="text-sm text-zinc-500 dark:text-zinc-400">No attachments.</p>
      ) : (
        <ul className="flex flex-col gap-3">
          {attachments.map((attachment) => (
            <AttachmentRow key={attachment.filename} attachment={attachment} />
          ))}
        </ul>
      )}
    </Card>
  );
}

function AttachmentRow({ attachment }: { attachment: Attachment }) {
  const analysis = attachment.analysis;
  const detection = analysis?.detection;

  // O nome diz um formato e os bytes dizem outro: e o achado que esta tela
  // existe para evidenciar.
  const disguised = detection?.mismatch === "executable_disguised";

  return (
    <li
      className={`rounded border p-3 ${
        disguised
          ? "border-red-500/30 bg-red-500/5"
          : "border-zinc-200 dark:border-zinc-800"
      }`}
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <span className="min-w-0 font-mono text-xs break-all">{attachment.filename}</span>
        {analysis && <Badge label={analysis.risk.level} tone={analysis.risk.level} />}
      </div>

      <dl className="mt-2 flex flex-col gap-0.5 text-[11px]">
        <Row label="size">{formatBytes(attachment.size)}</Row>
        <Row label="declared type">{attachment.declared_content_type}</Row>

        {detection && (
          <Row label="detected type" alert={disguised}>
            {detection.detected_name ?? "not recognised"}
          </Row>
        )}

        {analysis && (
          <Row label="risk score">
            {analysis.risk.score} / 100 — {analysis.risk.indicators.length} indicator
            {analysis.risk.indicators.length === 1 ? "" : "s"}
          </Row>
        )}
      </dl>

      {!analysis && (
        <p className="mt-2 text-[11px] text-zinc-500 dark:text-zinc-400">
          Not analysed: the recursion depth limit was reached. The attachment is
          still listed, because hiding it would be worse than not inspecting it.
        </p>
      )}
    </li>
  );
}

function Row({
  label,
  children,
  alert = false,
}: {
  label: string;
  children: React.ReactNode;
  alert?: boolean;
}) {
  return (
    <div className="flex flex-col gap-0.5 sm:flex-row sm:gap-3">
      <dt className="shrink-0 text-zinc-500 sm:w-32 dark:text-zinc-400">{label}</dt>
      <dd
        className={`min-w-0 font-mono break-all ${
          alert ? "font-medium text-red-600 dark:text-red-400" : ""
        }`}
      >
        {children}
      </dd>
    </div>
  );
}
