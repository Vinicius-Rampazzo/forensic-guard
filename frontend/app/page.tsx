/**
 * Pagina unica do ForensicGuard.
 *
 * Quatro estados, um de cada vez:
 *
 *   idle      -> area de upload
 *   analysing -> indicador de progresso
 *   done      -> relatorio
 *   failed    -> mensagem de erro e caminho de volta
 *
 * Nao ha rota /report porque nao ha persistencia: sem banco, um relatorio nao
 * tem endereco proprio. Criar /report/:id seria prometer um link que nao
 * funcionaria se alguem o compartilhasse.
 */

"use client";

import { useEffect, useRef, useState } from "react";

import { AnalysisLoading } from "@/components/AnalysisLoading";
import { AnalysisReport } from "@/components/AnalysisReport";
import { FileDropzone } from "@/components/FileDropzone";
import { formatBytes } from "@/components/FileOverview";
import { analyzeEvidence, getHealth } from "@/services/api";
import type { AnalysisResult } from "@/types/analysis";

type ApiStatus = "checking" | "online" | "offline";

type Screen =
  | { state: "idle" }
  | { state: "analysing"; filename: string }
  | { state: "done"; result: AnalysisResult }
  | { state: "failed"; message: string };

export default function Home() {
  const [screen, setScreen] = useState<Screen>({ state: "idle" });
  const [apiStatus, setApiStatus] = useState<ApiStatus>("checking");

  // Limite de upload informado pelo backend. Null enquanto a checagem de
  // saude nao respondeu - nesse caso nao ha como validar antes, e o servidor
  // continua sendo a ultima palavra.
  const [uploadLimit, setUploadLimit] = useState<number | null>(null);

  // Guarda o controlador do envio em andamento para poder cancelar quando o
  // componente sair da tela. useRef porque trocar este valor nao deve
  // provocar uma nova renderizacao.
  const requestRef = useRef<AbortController | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    getHealth(controller.signal)
      .then((health) => {
        setApiStatus("online");
        setUploadLimit(health.max_upload_size);
      })
      .catch((error: unknown) => {
        if (error instanceof Error && error.name === "AbortError") return;
        setApiStatus("offline");
      });

    return () => controller.abort();
  }, []);

  useEffect(() => {
    // Cancela um envio em andamento se a pagina for desmontada.
    return () => requestRef.current?.abort();
  }, []);

  async function handleFile(file: File) {
    // Verificacao do tamanho ANTES de enviar.
    //
    // O navegador ja conhece o tamanho do arquivo, entao mandar 300 MB pela
    // rede so para receber um 413 e desperdicio - e a mensagem de erro fica
    // mais util quando diz os DOIS numeros, o do arquivo e o do limite.
    //
    // Isto nao substitui a verificacao do servidor: um cliente qualquer pode
    // ignorar esta checagem. Validacao no cliente e conveniencia; a do
    // servidor e que e seguranca.
    if (uploadLimit !== null && file.size > uploadLimit) {
      setScreen({
        state: "failed",
        message:
          `This file is ${formatBytes(file.size)}, and the server accepts up to ` +
          `${formatBytes(uploadLimit)}. The limit is configurable in ` +
          `backend/.env via MAX_UPLOAD_SIZE.`,
      });
      return;
    }

    requestRef.current?.abort();

    const controller = new AbortController();
    requestRef.current = controller;

    setScreen({ state: "analysing", filename: file.name });

    try {
      const result = await analyzeEvidence(file, controller.signal);
      setScreen({ state: "done", result });
    } catch (error) {
      // Cancelamento nao e falha e nao deve virar tela de erro.
      if (error instanceof Error && error.name === "AbortError") return;

      setScreen({
        state: "failed",
        message: error instanceof Error ? error.message : "Analysis failed.",
      });
    }
  }

  return (
    <main className="mx-auto flex w-full max-w-4xl flex-1 flex-col gap-8 px-6 py-12">
      <Header apiStatus={apiStatus} showReset={screen.state !== "idle"} onReset={() => setScreen({ state: "idle" })} />

      {screen.state === "idle" && (
        <FileDropzone
          onFileSelected={handleFile}
          disabled={apiStatus === "offline"}
          uploadLimit={uploadLimit}
        />
      )}

      {screen.state === "analysing" && <AnalysisLoading filename={screen.filename} />}

      {screen.state === "done" && <AnalysisReport result={screen.result} />}

      {screen.state === "failed" && (
        <FailureNotice
          message={screen.message}
          onRetry={() => setScreen({ state: "idle" })}
        />
      )}

      {apiStatus === "offline" && screen.state === "idle" && (
        <p className="rounded-lg border border-amber-500/40 bg-amber-500/5 p-4 text-sm text-amber-600 dark:text-amber-400">
          The backend is not responding. Start it with{" "}
          <code className="font-mono">python backend/dev.py</code> and reload this page.
        </p>
      )}

      <Footer />
    </main>
  );
}

function Header({
  apiStatus,
  showReset,
  onReset,
}: {
  apiStatus: ApiStatus;
  showReset: boolean;
  onReset: () => void;
}) {
  const statusStyle = {
    checking: "border-zinc-500/40 bg-zinc-500/10 text-zinc-500",
    online: "border-emerald-500/40 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
    offline: "border-red-500/40 bg-red-500/10 text-red-600 dark:text-red-400",
  }[apiStatus];

  const statusLabel = {
    checking: "checking API",
    online: "API online",
    offline: "API offline",
  }[apiStatus];

  return (
    <header className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-xl font-semibold tracking-tight">ForensicGuard</h1>

        <div className="flex items-center gap-3">
          {showReset && (
            <button
              type="button"
              onClick={onReset}
              className="rounded-md border border-zinc-300 px-3 py-1.5 text-xs font-medium transition-colors hover:border-zinc-500 dark:border-zinc-700"
            >
              Analyse another file
            </button>
          )}

          <span
            className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium ${statusStyle}`}
          >
            <span className="h-1.5 w-1.5 rounded-full bg-current" />
            {statusLabel}
          </span>
        </div>
      </div>

      <p className="text-sm text-zinc-500 dark:text-zinc-400">
        Lightweight digital evidence analyzer. Files are removed after
        processing — nothing is stored.
      </p>
    </header>
  );
}

function FailureNotice({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="flex flex-col items-start gap-3 rounded-lg border border-red-500/40 bg-red-500/5 p-5">
      <h2 className="text-sm font-semibold text-red-600 dark:text-red-400">
        Analysis failed
      </h2>
      <p className="text-sm text-zinc-600 dark:text-zinc-400">{message}</p>
      <button
        type="button"
        onClick={onRetry}
        className="rounded-md border border-zinc-300 px-3 py-1.5 text-xs font-medium transition-colors hover:border-zinc-500 dark:border-zinc-700"
      >
        Try another file
      </button>
    </div>
  );
}

function Footer() {
  return (
    <footer className="mt-auto flex flex-col gap-1 border-t border-zinc-100 pt-6 text-xs text-zinc-400 dark:border-zinc-900 dark:text-zinc-600">
      <p className="font-medium">
        Privacy first — no database, no account, no permanent evidence storage.
      </p>
      <p>
        Static triage based on indicators and heuristics. Not a definitive
        malware or phishing verdict.
      </p>
    </footer>
  );
}
