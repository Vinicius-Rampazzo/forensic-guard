/**
 * Visao geral da evidencia: tamanho, entropia e identificacao do formato.
 */

import { Card, DataList, DataRow, Empty } from "@/components/Card";
import type { Detection, FileOverview as FileOverviewData } from "@/types/analysis";

/** Converte bytes em texto legivel: 84921 -> "82.9 KB". */
export function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 bytes";

  const units = ["bytes", "KB", "MB", "GB"];
  const exponent = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const value = bytes / 1024 ** exponent;

  return `${exponent === 0 ? value : value.toFixed(1)} ${units[exponent]}`;
}

/** Texto curto explicando o que a entropia observada sugere. */
function describeEntropy(entropy: number): string {
  if (entropy > 7.5) return "compressed, encrypted or packed";
  if (entropy > 6) return "binary content";
  if (entropy > 3) return "mostly text";
  return "highly repetitive";
}

interface FileOverviewProps {
  file: FileOverviewData;
  detection: Detection;
}

export function FileOverview({ file, detection }: FileOverviewProps) {
  return (
    <div className="flex flex-col gap-4">
      <Card title="File">
        <DataList>
          <DataRow label="Size">
            {formatBytes(file.size)}{" "}
            <span className="text-zinc-400 dark:text-zinc-600">
              ({file.size.toLocaleString("en-US")} bytes)
            </span>
          </DataRow>

          <DataRow label="Entropy">
            <span className="tabular-nums">{file.entropy.toFixed(4)}</span>
            <span className="text-zinc-400 dark:text-zinc-600"> / 8.00</span>
            <span className="ml-2 text-zinc-500 dark:text-zinc-400">
              — {describeEntropy(file.entropy)}
            </span>
          </DataRow>
        </DataList>
      </Card>

      <Card
        title="Type detection"
        hint="What the file claims to be, compared with what its bytes say it is."
      >
        <DataList>
          <DataRow label="Declared extension" mono>
            {detection.declared_extension || <Empty>none</Empty>}
          </DataRow>

          <DataRow label="Detected format">
            {detection.detected_name ?? <Empty>not recognised</Empty>}
          </DataRow>

          <DataRow label="Detected MIME" mono>
            {detection.detected_mime ?? <Empty>—</Empty>}
          </DataRow>

          <DataRow label="Evidence strength">
            {detection.confirmed_bytes > 0 ? (
              <>
                {detection.confirmed_bytes} byte
                {detection.confirmed_bytes === 1 ? "" : "s"} confirmed
                <span className="ml-2 text-zinc-500 dark:text-zinc-400">
                  — {detection.confirmed_bytes <= 2 ? "weak signature" : "strong signature"}
                </span>
              </>
            ) : (
              <Empty>no signature matched</Empty>
            )}
          </DataRow>

          <DataRow label="Second opinion" mono>
            {detection.puremagic_mime ?? <Empty>no opinion</Empty>}
            {detection.second_opinion_agrees === false && (
              <span className="ml-2 font-sans text-amber-600 dark:text-amber-400">
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
          <ul className="mt-3 flex flex-col gap-1 border-t border-zinc-100 pt-3 dark:border-zinc-900">
            {detection.notes.map((note) => (
              <li key={note} className="text-xs text-zinc-500 dark:text-zinc-400">
                {note}
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
