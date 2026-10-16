/**
 * Estado de espera durante a analise.
 *
 * Mostra o nome do arquivo em vez de um "carregando..." generico: quem acabou
 * de arrastar um arquivo quer confirmar que foi o arquivo certo que saiu.
 */

export function AnalysisLoading({ filename }: { filename: string }) {
  return (
    <div className="flex flex-col items-center gap-4 rounded-xl border border-zinc-200 px-6 py-16 text-center dark:border-zinc-800">
      {/*
        aria-hidden porque o circulo girando e puramente decorativo. O texto
        abaixo ja informa o que esta acontecendo, e anunciar os dois seria
        redundante para quem usa leitor de tela.
      */}
      <span
        aria-hidden
        className="h-6 w-6 animate-spin rounded-full border-2 border-zinc-300 border-t-emerald-500 dark:border-zinc-700"
      />

      <div className="flex flex-col gap-1">
        {/*
          aria-live avisa o leitor de tela quando este texto aparece, sem
          roubar o foco de onde o usuario estava.
        */}
        <p className="text-sm font-medium" aria-live="polite">
          Analysing evidence
        </p>
        <p className="max-w-full truncate font-mono text-xs text-zinc-500 dark:text-zinc-400">
          {filename}
        </p>
      </div>
    </div>
  );
}
