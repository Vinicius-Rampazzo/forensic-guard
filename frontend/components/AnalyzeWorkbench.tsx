/**
 * Bancada de analise - o que era a parte funcional de `app/page.tsx`.
 *
 * Quatro estados, um de cada vez:
 *
 *   idle      -> area de upload e campo de link
 *   analysing -> esqueleto do relatorio
 *   done      -> relatorio de arquivo
 *   doneUrl   -> relatorio de URL
 *   failed    -> mensagem de erro e caminho de volta
 *
 * O institucional saiu daqui e virou a rota `/`. O relatorio, nao: continua
 * sendo estado desta tela, e nao uma rota propria. O motivo e o mesmo de
 * sempre - sem banco de dados um relatorio nao tem endereco. Criar
 * `/report/:id` seria prometer um link que nao funcionaria se alguem o
 * compartilhasse.
 */

"use client";

import { AlertCircle, RotateCcw, ShieldAlert } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";

import { AnalysisLoading } from "@/components/AnalysisLoading";
import { AnalysisReport } from "@/components/AnalysisReport";
import { EmptyState } from "@/components/EmptyState";
import { UrlReport } from "@/components/UrlReport";
import { formatBytes } from "@/components/format";
import { useApiHealth } from "@/components/useApiHealth";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { analyzeEvidence, analyzeUrl } from "@/services/api";
import type { AnalysisResult, UrlAnalysisResult } from "@/types/analysis";

type Screen =
  | { state: "idle" }
  | { state: "analysing"; filename: string }
  | { state: "done"; result: AnalysisResult }
  | { state: "doneUrl"; result: UrlAnalysisResult }
  | { state: "failed"; message: string };

export function AnalyzeWorkbench() {
  const tErrors = useTranslations("errors");
  const tApp = useTranslations("app");

  const [screen, setScreen] = useState<Screen>({ state: "idle" });
  const { status: apiStatus, uploadLimit } = useApiHealth();

  // Guarda o controlador do envio em andamento para poder cancelar quando o
  // componente sair da tela. useRef porque trocar este valor nao deve
  // provocar uma nova renderizacao.
  const requestRef = useRef<AbortController | null>(null);

  useEffect(() => {
    // Cancela um envio em andamento se a pagina for desmontada.
    return () => requestRef.current?.abort();
  }, []);

  useEffect(() => {
    // Volta ao topo a cada troca de estado.
    //
    // A navegacao entre `/` e `/analyze` o Next ja resolve sozinho, porque sao
    // rotas. Aqui dentro nao: ir de "idle" para "done" nao muda a URL, e sem
    // este efeito quem rolou a area de upload cairia no meio do relatorio.
    //
    // `instant` e deliberado: uma rolagem suave competiria com a animacao de
    // entrada do conteudo novo.
    window.scrollTo({ top: 0, behavior: "instant" });
  }, [screen.state]);

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

  const showingReport = screen.state === "done" || screen.state === "doneUrl";

  return (
    /*
      A chave muda a cada troca de estado, entao o React recria a arvore e a
      animacao de entrada roda de novo - sem isso a troca seria um corte seco
      entre dois conteudos completamente diferentes.
    */
    <main key={screen.state} className="fg-rise mx-auto w-full max-w-6xl flex-1 px-6 py-10">
      {/*
        "Analisar outro" ficava no cabecalho. Desceu para ca quando o
        cabecalho virou parte do layout: de la ele nao tem como zerar o estado
        desta tela, e um botao global que so funciona em uma pagina e pior que
        um botao local.
      */}
      {showingReport && (
        <div className="mb-5 flex justify-end">
          <Button variant="outline" size="sm" onClick={() => setScreen({ state: "idle" })}>
            <RotateCcw className="size-3.5" />
            {tApp("analyseAnother")}
          </Button>
        </div>
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
              command: () => <code className="font-mono text-xs">python backend/dev.py</code>,
            })}
          </AlertDescription>
        </Alert>
      )}
    </main>
  );
}
