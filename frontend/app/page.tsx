/**
 * Landing do ForensicGuard.
 *
 * Nesta etapa a pagina prova apenas uma coisa: o frontend fala com o backend.
 * O dropzone de upload e o relatorio entram na etapa de interface.
 *
 * `"use client"` marca este arquivo como Client Component. Por padrao, no App
 * Router, todo componente e Server Component: renderiza no servidor e chega ao
 * navegador como HTML pronto, sem JavaScript. Isso e otimo para conteudo
 * estatico, mas impede useState, useEffect e qualquer interatividade.
 *
 * Aqui precisamos de estado (checking -> online/offline) e de um efeito que
 * roda no navegador, entao o componente precisa ser de cliente.
 */

"use client";

import { useEffect, useState } from "react";

import { getHealth } from "@/services/api";

/**
 * Os tres estados obrigatorios de qualquer chamada de rede.
 *
 * Ignorar "checking" produz um piscar de conteudo errado; ignorar "offline"
 * produz uma tela em branco sem explicacao. Este mesmo padrao se repete no
 * upload de evidencias mais adiante.
 */
type ApiStatus = "checking" | "online" | "offline";

const STATUS_LABEL: Record<ApiStatus, string> = {
  checking: "Checking API...",
  online: "API online",
  offline: "API offline",
};

const STATUS_STYLE: Record<ApiStatus, string> = {
  checking: "border-zinc-500/40 bg-zinc-500/10 text-zinc-400",
  online: "border-emerald-500/40 bg-emerald-500/10 text-emerald-400",
  offline: "border-red-500/40 bg-red-500/10 text-red-400",
};

function ApiStatusBadge() {
  const [status, setStatus] = useState<ApiStatus>("checking");
  const [version, setVersion] = useState<string | null>(null);

  useEffect(() => {
    // O AbortController cancela a requisicao se o componente sair da tela
    // antes da resposta chegar - evita atualizar o estado de algo que ja
    // nao existe mais.
    const controller = new AbortController();

    getHealth(controller.signal)
      .then((health) => {
        setStatus("online");
        setVersion(health.version);
      })
      .catch((error: unknown) => {
        // Cancelamento nao e falha: nao deve pintar a tela de vermelho.
        if (error instanceof Error && error.name === "AbortError") return;
        setStatus("offline");
      });

    return () => controller.abort();
  }, []);

  return (
    <div
      className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-medium ${STATUS_STYLE[status]}`}
    >
      <span className="relative flex h-2 w-2">
        {status === "checking" && (
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-current opacity-60" />
        )}
        <span className="relative inline-flex h-2 w-2 rounded-full bg-current" />
      </span>
      {STATUS_LABEL[status]}
      {version && <span className="opacity-60">v{version}</span>}
    </div>
  );
}

const SUPPORTED_FORMATS = ["JPG", "PNG", "PDF", "EML", "DOCX", "EXE"];

export default function Home() {
  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col justify-center gap-10 px-6 py-16">
      <header className="flex flex-col gap-4">
        <ApiStatusBadge />

        <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">ForensicGuard</h1>

        <p className="text-lg text-zinc-500 dark:text-zinc-400">
          Lightweight digital evidence analyzer. Inspect files, images and emails for suspicious
          indicators, metadata anomalies and potential security threats.
        </p>
      </header>

      <section
        aria-label="Evidence upload"
        className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-zinc-300 px-6 py-14 text-center dark:border-zinc-700"
      >
        <p className="text-sm font-medium text-zinc-500 dark:text-zinc-400">
          Evidence upload arrives in the next stage
        </p>
        <p className="font-mono text-xs text-zinc-400 dark:text-zinc-600">
          {SUPPORTED_FORMATS.join(" • ")}
        </p>
      </section>

      <footer className="flex flex-col gap-2 text-xs text-zinc-400 dark:text-zinc-600">
        <p className="font-medium">
          Privacy first — no database, no account, no permanent evidence storage.
        </p>
        <p>
          The ForensicGuard risk score is based on static indicators and heuristics. It does not
          provide a definitive malware or phishing verdict.
        </p>
      </footer>
    </main>
  );
}
