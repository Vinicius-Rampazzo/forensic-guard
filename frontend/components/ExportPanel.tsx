/**
 * Exportacao do relatorio em JSON e em HTML.
 *
 * Por que o HTML e gerado no NAVEGADOR
 * ------------------------------------
 * Todos os dados ja estao aqui - o relatorio na tela e exatamente o que seria
 * exportado. Pedir ao backend que gerasse o mesmo arquivo significaria manter
 * duas versoes do mesmo layout, em duas linguagens, que divergiriam na
 * primeira mudanca.
 *
 * O arquivo gerado e AUTOCONTIDO: estilos embutidos, nenhum script, nenhuma
 * fonte externa, nenhuma requisicao. Abre em qualquer navegador, sem servidor
 * e sem internet - que e o requisito de um relatorio pericial, porque ele
 * precisa continuar legivel daqui a anos e sem depender de nada.
 */

"use client";

import { Download, FileCode, FileJson } from "lucide-react";
import { useTranslations } from "next-intl";

import { Card } from "@/components/Card";
import { Button } from "@/components/ui/button";
import { buildHtmlReport } from "@/lib/html-report";
import type { AnalysisResult } from "@/types/analysis";

export function ExportPanel({ result }: { result: AnalysisResult }) {
  const t = useTranslations("export");

  function downloadJson() {
    const content = JSON.stringify(result, null, 2);
    download(content, `${baseName(result.filename)}.forensicguard.json`, "application/json");
  }

  function downloadHtml() {
    download(
      buildHtmlReport(result),
      `${baseName(result.filename)}.forensicguard.html`,
      "text/html",
    );
  }

  return (
    <Card title={t("json").replace(/^\w+\s/, "")} hint={t("hint")}>
      <div className="flex flex-wrap gap-2">
        <Button variant="outline" size="sm" onClick={downloadJson} className="gap-2">
          <FileJson className="size-4" />
          {t("json")}
          <Download className="size-3.5 opacity-60" />
        </Button>

        <Button variant="outline" size="sm" onClick={downloadHtml} className="gap-2">
          <FileCode className="size-4" />
          {t("html")}
          <Download className="size-3.5 opacity-60" />
        </Button>
      </div>
    </Card>
  );
}

/**
 * Dispara o download de um conteudo gerado em memoria.
 *
 * O caminho e sempre o mesmo: embrulha o texto num Blob, cria uma URL
 * temporaria para ele, simula um clique num link com o atributo `download`, e
 * libera a URL em seguida.
 *
 * `revokeObjectURL` nao e opcional. Cada URL criada segura o Blob inteiro na
 * memoria ate ser liberada - sem isso, exportar varios relatorios grandes
 * acumularia todos eles.
 */
function download(content: string, filename: string, mimeType: string) {
  const blob = new Blob([content], { type: `${mimeType};charset=utf-8` });
  const url = URL.createObjectURL(blob);

  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();

  URL.revokeObjectURL(url);
}

/** Remove a extensao do nome original, para montar o nome do arquivo exportado. */
function baseName(filename: string): string {
  const withoutPath = filename.split(/[\\/]/).pop() ?? filename;
  const dot = withoutPath.lastIndexOf(".");

  return dot > 0 ? withoutPath.slice(0, dot) : withoutPath;
}
