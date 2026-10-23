/**
 * Geracao do relatorio HTML autocontido.
 *
 * O arquivo resultante nao depende de nada: sem servidor, sem internet, sem
 * JavaScript, sem fontes externas. Abre com dois cliques em qualquer
 * navegador, hoje ou daqui a dez anos.
 *
 * Esse requisito nao e capricho. Um relatorio pericial e anexado a processos,
 * arquivado e lido por pessoas que nao tem a ferramenta instalada - e qualquer
 * dependencia externa e um ponto onde ele pode deixar de abrir.
 *
 * SEGURANCA
 * ---------
 * Todo o conteudo vem de um arquivo nao confiavel: nomes, strings extraidas,
 * cabecalhos de e-mail. Nada disso entra no HTML sem passar por `escapeHtml`.
 * Um relatorio forense que executa o conteudo que esta analisando seria uma
 * ironia cara.
 */

import type { AnalysisResult, Indicator } from "@/types/analysis";

/** Escapa os cinco caracteres que tem significado em HTML. */
function escapeHtml(value: unknown): string {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

const SEVERITY_COLORS: Record<string, string> = {
  info: "#38bdf8",
  low: "#10b981",
  medium: "#f59e0b",
  high: "#f97316",
  critical: "#ef4444",
};

/**
 * Estilos embutidos no proprio arquivo.
 *
 * Escritos a mao, sem Tailwind: o CSS gerado pelo Tailwind depende do processo
 * de build e traz milhares de regras nao usadas. Aqui sao algumas dezenas de
 * linhas que cobrem exatamente o que o relatorio precisa.
 */
const STYLES = `
  :root { color-scheme: light dark; }
  * { box-sizing: border-box; }
  body {
    margin: 0; padding: 2rem 1.5rem;
    font: 14px/1.6 ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
    background: #09090b; color: #e4e4e7;
  }
  main { max-width: 56rem; margin: 0 auto; }
  h1 { font-size: 1.25rem; margin: 0 0 .25rem; }
  h2 { font-size: .95rem; margin: 2rem 0 .75rem; padding-bottom: .4rem; border-bottom: 1px solid #27272a; }
  h3 { font-size: .8rem; margin: 0 0 .35rem; }
  code, .mono { font-family: ui-monospace, "SFMono-Regular", Menlo, monospace; }
  .muted { color: #a1a1aa; }
  .small { font-size: .75rem; }
  .score { display: flex; align-items: baseline; gap: .5rem; margin: 1rem 0 .5rem; }
  .score strong { font-size: 2.5rem; font-weight: 600; }
  .bar { height: 6px; border-radius: 999px; background: #27272a; overflow: hidden; }
  .bar > div { height: 100%; border-radius: 999px; }
  .badge {
    display: inline-block; padding: .1rem .45rem; border-radius: 4px;
    border: 1px solid currentColor; font-size: .65rem;
    text-transform: uppercase; letter-spacing: .05em;
  }
  table { width: 100%; border-collapse: collapse; }
  td, th { text-align: left; padding: .35rem .5rem; border-bottom: 1px solid #1c1c1f; vertical-align: top; }
  th { width: 12rem; color: #a1a1aa; font-weight: 400; font-size: .75rem; }
  td { font-size: .8rem; word-break: break-word; }
  .indicator { border: 1px solid #27272a; border-radius: 8px; padding: .85rem; margin-bottom: .6rem; }
  .indicator header { display: flex; justify-content: space-between; gap: 1rem; align-items: start; }
  .evidence { margin-top: .6rem; padding: .6rem; border-radius: 6px; background: #121214; font-size: .7rem; }
  .list { margin: 0; padding: 0; list-style: none; }
  .list li { padding: .25rem .5rem; background: #121214; border-radius: 4px; margin-bottom: .2rem; font-size: .7rem; word-break: break-all; }
  footer { margin-top: 2.5rem; padding-top: 1rem; border-top: 1px solid #27272a; color: #71717a; font-size: .7rem; }
  @media print { body { background: #fff; color: #000; } .indicator, td, th, h2 { border-color: #ddd; } .evidence, .list li { background: #f4f4f5; } }
`;

export function buildHtmlReport(result: AnalysisResult): string {
  const generatedAt = new Date().toISOString();

  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ForensicGuard — ${escapeHtml(result.filename)}</title>
<style>${STYLES}</style>
</head>
<body>
<main>
  <h1>ForensicGuard</h1>
  <p class="muted small">Digital evidence report · generated ${escapeHtml(generatedAt)}</p>

  <h2>Evidence</h2>
  ${table([
    ["Filename", escapeHtml(result.filename)],
    ["Size", `${result.file.size.toLocaleString("en-US")} bytes`],
    ["Declared extension", escapeHtml(result.detection.declared_extension || "—")],
    ["Detected format", escapeHtml(result.detection.detected_name ?? "not recognised")],
    ["Detected MIME", escapeHtml(result.detection.detected_mime ?? "—")],
    ["Evidence type", escapeHtml(result.detection.evidence_type)],
    ["Entropy", `${result.file.entropy.toFixed(4)} / 8.00`],
  ])}

  <h2>Risk</h2>
  <div class="score">
    <strong style="color:${SEVERITY_COLORS[result.risk.level]}">${result.risk.score}</strong>
    <span class="muted">/ 100</span>
    <span class="badge" style="color:${SEVERITY_COLORS[result.risk.level]}">${escapeHtml(result.risk.level)}</span>
  </div>
  <div class="bar"><div style="width:${result.risk.score}%;background:${SEVERITY_COLORS[result.risk.level]}"></div></div>

  <h2>Indicators (${result.risk.indicators.length})</h2>
  ${
    result.risk.indicators.length === 0
      ? `<p class="muted small">No indicators found. Static triage did not flag anything — which is not the same as saying the file is safe.</p>`
      : result.risk.indicators.map(indicatorBlock).join("")
  }

  <h2>Hashes</h2>
  ${table(
    Object.entries(result.file.hashes).map(([algorithm, value]) => [
      algorithm.toUpperCase(),
      `<code>${escapeHtml(value)}</code>`,
    ]),
  )}

  ${artifactsSection(result)}
  ${imageSection(result)}
  ${emailSection(result)}

  <footer>
    ${escapeHtml(result.disclaimer)}
    <br><br>
    This report is self-contained: no server, no internet connection and no
    scripts are needed to read it.
  </footer>
</main>
</body>
</html>`;
}

function table(rows: [string, string][]): string {
  return `<table>${rows
    .map(([label, value]) => `<tr><th>${escapeHtml(label)}</th><td>${value}</td></tr>`)
    .join("")}</table>`;
}

function indicatorBlock(indicator: Indicator): string {
  const colour = SEVERITY_COLORS[indicator.severity] ?? "#a1a1aa";

  const evidence = Object.entries(indicator.evidence)
    .map(
      ([key, value]) =>
        `<div><span class="muted mono">${escapeHtml(key)}:</span> <span class="mono">${escapeHtml(
          formatEvidenceValue(value),
        )}</span></div>`,
    )
    .join("");

  return `<div class="indicator">
    <header>
      <h3>${escapeHtml(indicator.title)}</h3>
      <div style="white-space:nowrap">
        <span class="badge" style="color:${colour}">${escapeHtml(indicator.severity)}</span>
        <span class="mono small muted">${indicator.score > 0 ? `+${indicator.score}` : "0"}</span>
      </div>
    </header>
    <p class="muted small" style="margin:.4rem 0 0">${escapeHtml(indicator.description)}</p>
    <p class="mono small muted" style="margin:.35rem 0 0">${escapeHtml(indicator.id)}</p>
    ${evidence ? `<div class="evidence">${evidence}</div>` : ""}
  </div>`;
}

function formatEvidenceValue(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (Array.isArray(value)) return value.map(formatEvidenceValue).join(", ");
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function artifactsSection(result: AnalysisResult): string {
  const entries = Object.entries(result.strings.artifacts).filter(
    ([, values]) => Array.isArray(values) && values.length > 0,
  ) as [string, string[]][];

  if (entries.length === 0) return "";

  return `<h2>Artifacts</h2>${entries
    .map(
      ([category, values]) =>
        `<h3 class="muted">${escapeHtml(category)} (${values.length})</h3>
         <ul class="list">${values
           .map((value) => `<li>${escapeHtml(value)}</li>`)
           .join("")}</ul>`,
    )
    .join("")}`;
}

function imageSection(result: AnalysisResult): string {
  const image = result.image;

  if (!image) return "";

  const rows: [string, string][] = [
    ["Dimensions", image.width && image.height ? `${image.width} × ${image.height} px` : "—"],
    ["Format", escapeHtml(image.image_format ?? "—")],
    ["Colour mode", escapeHtml(image.color_mode ?? "—")],
    ["Device", escapeHtml([image.device_make, image.device_model].filter(Boolean).join(" ") || "—")],
    ["Software", escapeHtml(image.software ?? "—")],
    ["Recorded at", escapeHtml(image.created_at ?? "—")],
    [
      "GPS",
      image.gps ? `${image.gps.latitude}, ${image.gps.longitude}` : "not present",
    ],
  ];

  return `<h2>Image metadata</h2>${table(rows)}`;
}

function emailSection(result: AnalysisResult): string {
  const email = result.email;

  if (!email) return "";

  const headers = Object.entries(email.headers).map(
    ([name, value]) => [name, escapeHtml(value)] as [string, string],
  );

  const auth: [string, string][] = [
    ["SPF", escapeHtml(email.authentication.spf ?? "not reported")],
    ["DKIM", escapeHtml(email.authentication.dkim ?? "not reported")],
    ["DMARC", escapeHtml(email.authentication.dmarc ?? "not reported")],
    ["Reply-To mismatch", email.reply_to_mismatch ? "yes" : "no"],
    ["Return-Path mismatch", email.return_path_mismatch ? "yes" : "no"],
  ];

  const attachments = email.attachments.length
    ? `<h3 class="muted">Attachments (${email.attachments.length})</h3>
       <ul class="list">${email.attachments
         .map(
           (attachment) =>
             `<li>${escapeHtml(attachment.filename)} — declared ${escapeHtml(
               attachment.declared_content_type,
             )}, detected ${escapeHtml(
               attachment.analysis?.detection.detected_name ?? "not analysed",
             )}${
               attachment.analysis
                 ? ` — risk ${attachment.analysis.risk.score}/100 ${attachment.analysis.risk.level}`
                 : ""
             }</li>`,
         )
         .join("")}</ul>`
    : "";

  return `<h2>Email headers</h2>${table(headers)}
          <h2>Authentication</h2>${table(auth)}
          ${attachments}`;
}
