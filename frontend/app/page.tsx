/**
 * Pagina unica do ForensicGuard.
 *
 * Quatro estados, um de cada vez:
 *
 *   idle      -> o que a ferramenta faz + area de upload
 *   analysing -> esqueleto do relatorio
 *   done      -> relatorio
 *   failed    -> mensagem de erro e caminho de volta
 *
 * Nao ha rota /report porque nao ha persistencia: sem banco, um relatorio nao
 * tem endereco proprio. Criar /report/:id seria prometer um link que nao
 * funcionaria se alguem o compartilhasse.
 */

"use client";

import { AlertCircle, ShieldAlert } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";

import { AnalysisLoading } from "@/components/AnalysisLoading";
import { AnalysisReport } from "@/components/AnalysisReport";
import { EmptyState } from "@/components/EmptyState";
import { LandingScreen } from "@/components/LandingScreen";
import { LanguageToggle } from "@/components/LanguageToggle";
import { Logo, Wordmark } from "@/components/Logo";
import { ThemeToggle } from "@/components/ThemeToggle";
import { formatBytes } from "@/components/format";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { UrlReport } from "@/components/UrlReport";
import { analyzeEvidence, analyzeUrl, getHealth } from "@/services/api";
import { cn } from "@/lib/utils";
import type { AnalysisResult, UrlAnalysisResult } from "@/types/analysis";

type ApiStatus = "checking" | "online" | "offline";

type Screen =
  | { state: "landing" }
  | { state: "idle" }
  | { state: "analysing"; filename: string }
  | { state: "done"; result: AnalysisResult }
  | { state: "doneUrl"; result: UrlAnalysisResult }
  | { state: "failed"; message: string };

export default function Home() {
  const tErrors = useTranslations("errors");
  const tApp = useTranslations("app");

  const [screen, setScreen] = useState<Screen>({ state: "landing" });
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
    // O navegador ja conhece o tamanho do arquivo, entao mandar centenas de
    // megabytes pela rede so para receber um 413 e desperdicio - e a mensagem
    // fica mais util quando diz os DOIS numeros.
    //
    // Isto nao substitui a verificacao do servidor: um cliente qualquer pode
    // ignorar esta checagem. Validacao no cliente e conveniencia; a do
    // servidor e que e seguranca.
    if (uploadLimit !== null && file.size > uploadLimit) {
      setScreen({
        state: "failed",
        message: tErrors("tooLarge", {
          size: formatBytes(file.size),
          limit: formatBytes(uploadLimit),
        }),
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
        message: error instanceof Error ? error.message : tErrors("generic"),
      });
    }
  }

  async function handleUrl(url: string) {
    requestRef.current?.abort();

    const controller = new AbortController();
    requestRef.current = controller;

    // O rotulo exibido durante a espera e a propria URL, cortada. Mostrar o
    // que esta sendo analisado confirma que foi o endereco certo que saiu.
    setScreen({
      state: "analysing",
      filename: url.length > 70 ? `${url.slice(0, 67)}...` : url,
    });

    try {
      const result = await analyzeUrl(url, controller.signal);
      setScreen({ state: "doneUrl", result });
    } catch (error) {
      if (error instanceof Error && error.name === "AbortError") return;

      setScreen({
        state: "failed",
        message: error instanceof Error ? error.message : tErrors("generic"),
      });
    }
  }

  return (
    <div className="flex min-h-full flex-col">
      <AppHeader
        apiStatus={apiStatus}
        showReset={
          screen.state === "done" ||
          screen.state === "doneUrl" ||
          screen.state === "failed"
        }
        onReset={() => setScreen({ state: "idle" })}
        onHome={() => setScreen({ state: "landing" })}
      />

      {/*
        A chave muda a cada troca de tela, entao o React recria a arvore e a
        animacao de entrada roda de novo - sem isso a troca seria um corte
        seco entre dois conteudos completamente diferentes.
      */}
      <main
        key={screen.state}
        className="fg-rise mx-auto w-full max-w-6xl flex-1 px-6 py-10"
      >
        {screen.state === "landing" && (
          <LandingScreen onEnter={() => setScreen({ state: "idle" })} />
        )}

        {screen.state === "idle" && (
          <EmptyState
            onFileSelected={handleFile}
            onUrlSubmitted={handleUrl}
            disabled={apiStatus === "offline"}
            uploadLimit={uploadLimit}
          />
        )}

        {screen.state === "analysing" && <AnalysisLoading filename={screen.filename} />}

        {screen.state === "done" && <AnalysisReport result={screen.result} />}

        {screen.state === "doneUrl" && <UrlReport result={screen.result} />}

        {screen.state === "failed" && (
          <Alert variant="destructive" className="mx-auto max-w-2xl">
            <AlertCircle />
            <AlertTitle>{tErrors("failedTitle")}</AlertTitle>
            <AlertDescription>
              <p>{screen.message}</p>
              <Button
                variant="outline"
                size="sm"
                className="mt-3"
                onClick={() => setScreen({ state: "idle" })}
              >
                {tErrors("tryAnother")}
              </Button>
            </AlertDescription>
          </Alert>
        )}

        {apiStatus === "offline" && screen.state === "idle" && (
          <Alert className="mx-auto mt-8 max-w-2xl">
            <ShieldAlert />
            <AlertTitle>{tApp("backendDownTitle")}</AlertTitle>
            <AlertDescription>
              {tApp.rich("backendDownBody", {
                command: () => (
                  <code className="font-mono text-xs">python backend/dev.py</code>
                ),
              })}
            </AlertDescription>
          </Alert>
        )}
      </main>

      <footer className="border-t">
        <div className="mx-auto flex w-full max-w-6xl flex-col gap-1 px-6 py-5 text-[11px] text-muted-foreground">
          <p className="font-medium">{tApp("privacyLine")}</p>
          <p>{tApp("disclaimerLine")}</p>
        </div>
      </footer>
    </div>
  );
}

function AppHeader({
  apiStatus,
  showReset,
  onReset,
  onHome,
}: {
  apiStatus: ApiStatus;
  showReset: boolean;
  onReset: () => void;
  onHome: () => void;
}) {
  const t = useTranslations("app");

  const status = {
    checking: { key: "apiChecking", dot: "bg-muted-foreground", text: "text-muted-foreground" },
    online: { key: "apiOnline", dot: "bg-emerald-500", text: "text-emerald-600 dark:text-emerald-400" },
    offline: { key: "apiOffline", dot: "bg-red-500", text: "text-red-600 dark:text-red-400" },
  }[apiStatus];

  return (
    <header className="sticky top-0 z-20 border-b bg-background/80 backdrop-blur">
      <div className="mx-auto flex w-full max-w-6xl items-center gap-4 px-6 py-2.5">
        {/*
          A marca leva de volta a tela de entrada. E a convencao que todo
          mundo ja conhece, e evita um botao "voltar" a mais no cabecalho.
        */}
        <button
          type="button"
          onClick={onHome}
          className="flex min-w-0 items-center gap-2 rounded-md transition-opacity hover:opacity-80"
        >
          <Logo className="size-7 shrink-0" />
          <Wordmark className="text-base" />
          <span className="hidden text-xs text-muted-foreground md:inline">
            {t("tagline")}
          </span>
        </button>

        <div className="ml-auto flex items-center gap-1.5">
          {showReset && (
            <Button variant="outline" size="sm" onClick={onReset}>
              {t("analyseAnother")}
            </Button>
          )}

          <span
            className={cn(
              "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium",
              status.text,
            )}
          >
            <span className={cn("size-1.5 rounded-full", status.dot)} />
            {t(status.key)}
          </span>

          <LanguageToggle />
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
