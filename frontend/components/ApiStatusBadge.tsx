/**
 * Selo de estado da API, com a explicacao ancorada nele.
 *
 * O selo agora aparece SEMPRE, inclusive quando esta tudo certo. Antes ele so
 * surgia em caso de problema, pelo argumento de que um indicador permanente
 * dizendo "tudo bem" e ruido.
 *
 * Esse argumento valia enquanto o backend era sempre local, onde ele esta no
 * ar ou nao esta, e quem rodou sabe qual dos dois. Com um servidor que hiberna
 * sozinho, o estado muda sem ninguem mexer em nada - e ai saber que ele ficou
 * pronto e informacao que a pessoa esta esperando, nao ruido.
 *
 * O balao abre sozinho enquanto o servidor sobe. Ele explica o que esta
 * acontecendo e aponta para o proprio selo, que e onde a resposta vai
 * aparecer: quem le o aviso aprende onde olhar da proxima vez.
 */

"use client";

import { useTranslations } from "next-intl";
import { type ReactNode, type Ref, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Popover, PopoverAnchor, PopoverContent } from "@/components/ui/popover";
import type { ApiStatus } from "@/components/ApiHealthProvider";
import { IS_LOCAL_API } from "@/services/api";
import { cn } from "@/lib/utils";

/** Duracao tipica de uma partida a frio, usada so para desenhar o progresso. */
const EXPECTED_WAKE_MS = 60_000;

export function ApiStatusBadge({
  status,
  wakingSince,
  onRetry,
}: {
  status: ApiStatus;
  wakingSince: number | null;
  onRetry: () => void;
}) {
  const t = useTranslations("app");

  /*
    O balao abre sozinho quando ha algo a explicar, e quem fechar na mao nao e
    incomodado de novo - ate o assunto mudar.

    Guardamos PARA QUAL estado ele foi fechado, em vez de um booleano que
    precisaria ser zerado quando o estado muda. Zerar exigiria um efeito, e
    `setState` dentro de efeito provoca renderizacao em cascata. Assim o
    "reset" acontece sozinho: estado novo, chave diferente, balao abre.
  */
  const [dismissedFor, setDismissedFor] = useState<ApiStatus | null>(null);

  const needsExplanation = status === "waking" || status === "offline";
  const open = needsExplanation && dismissedFor !== status;

  return (
    <Popover open={open} onOpenChange={(next) => !next && setDismissedFor(status)}>
      <PopoverAnchor asChild>
        {/*
          Desenhado como irmao do seletor de idioma e do seletor de tema:
          mesma altura, mesmo arredondamento, mesma fonte monoespacada de 11px,
          mesmo cinza. A versao anterior era uma pilula com borda e um spinner
          grande - linguagem visual propria no meio de tres controles que
          seguiam outra, e por isso parecia colada ali.

          A cor fica so no pontinho. Texto colorido competiria com o conteudo
          da pagina para dizer algo que o ponto ja diz.
        */}
        <Indicator
          interactive={needsExplanation}
          onClick={() => setDismissedFor(null)}
          className="inline-flex h-8 items-center gap-1.5 rounded-md px-2 font-mono text-[11px] text-muted-foreground transition-colors hover:bg-muted"
        >
          <StatusDot status={status} />
          {t(`api.${status}`)}
        </Indicator>
      </PopoverAnchor>

      <PopoverContent
        align="end"
        className="w-80"
        // Sem isto o Radix move o foco para dentro do balao assim que ele
        // abre. Como quem abriu foi o relogio e nao a pessoa, roubar o foco
        // atrapalharia quem estivesse no meio de outra coisa.
        onOpenAutoFocus={(event) => event.preventDefault()}
      >
        {status === "waking" ? (
          <WakingContent wakingSince={wakingSince} />
        ) : (
          <OfflineContent onRetry={onRetry} />
        )}
      </PopoverContent>
    </Popover>
  );
}

/**
 * Botao quando ha o que explicar, texto simples quando nao ha.
 *
 * As classes sao as mesmas nos dois casos, entao a aparencia nao muda - o que
 * muda e poder clicar. Um botao que nao faz nada ao ser clicado e pior que um
 * rotulo honesto.
 */
function Indicator({
  interactive,
  onClick,
  className,
  children,
  ref,
}: {
  interactive: boolean;
  onClick: () => void;
  className?: string;
  children: ReactNode;
  ref?: Ref<HTMLElement>;
}) {
  if (!interactive) {
    return (
      <span ref={ref as Ref<HTMLSpanElement>} className={className}>
        {children}
      </span>
    );
  }

  return (
    <button
      ref={ref as Ref<HTMLButtonElement>}
      type="button"
      onClick={onClick}
      className={className}
    >
      {children}
    </button>
  );
}

/**
 * Pontinho colorido de estado.
 *
 * Nos estados passageiros ele ganha um anel que se expande - o mesmo sinal de
 * "ao vivo" que praticamente todo painel usa. Diz "isto ainda vai mudar" sem
 * precisar de spinner, que num texto de 11px vira borrao.
 */
function StatusDot({ status }: { status: ApiStatus }) {
  const transient = status === "waking" || status === "checking";

  const color =
    status === "online"
      ? "bg-emerald-500"
      : status === "waking"
        ? "bg-amber-500"
        : status === "offline"
          ? "bg-red-500"
          : "bg-muted-foreground";

  return (
    <span aria-hidden className="relative flex size-1.5 shrink-0">
      {transient && (
        <span
          className={cn("absolute inline-flex size-full animate-ping rounded-full opacity-75", color)}
        />
      )}
      <span className={cn("relative inline-flex size-1.5 rounded-full", color)} />
    </span>
  );
}

/**
 * Conteudo do balao enquanto o servidor sobe.
 *
 * O contador vive aqui, e nao no hook de saude da API. Assim a batida de um
 * segundo re-renderiza so este bloco, e nao o cabecalho e a pagina inteira.
 */
function WakingContent({ wakingSince }: { wakingSince: number | null }) {
  const t = useTranslations("app");
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (wakingSince === null) return;

    const tick = () => setElapsed(Date.now() - wakingSince);

    tick();

    const timer = window.setInterval(tick, 1_000);

    return () => window.clearInterval(timer);
  }, [wakingSince]);

  // Teto em 95%: uma barra que chega a 100 e continua esperando e pior que
  // uma que admite nao saber a hora exata.
  const progress = Math.min(95, (elapsed / EXPECTED_WAKE_MS) * 100);

  return (
    <div className="flex flex-col gap-3">
      {/*
        Icone e titulo na mesma linha, com o anel pulsando em ambar. O aviso
        precisa parecer "em andamento" ja na primeira olhada - um paragrafo
        de texto cinza seria lido como mensagem de erro.
      */}
      <div className="flex items-center gap-2">
        <span className="relative flex size-2 shrink-0">
          <span className="absolute inline-flex size-full animate-ping rounded-full bg-amber-500 opacity-75" />
          <span className="relative inline-flex size-2 rounded-full bg-amber-500" />
        </span>
        <p className="text-sm font-semibold">{t("wakeTitle")}</p>
      </div>

      <p className="text-xs leading-relaxed text-muted-foreground">{t("wakeBody")}</p>

      <div className="flex flex-col gap-1.5">
        <div
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={Math.round(progress)}
          aria-label={t("wakeTitle")}
          className="h-1.5 w-full overflow-hidden rounded-full bg-muted"
        >
          <div
            className="h-full rounded-full transition-[width] duration-1000 ease-linear"
            style={{ width: `${progress}%`, background: "var(--brand-cyan-ink)" }}
          />
        </div>

        <p className="text-right font-mono text-[10px] text-muted-foreground tabular-nums">
          {Math.floor(elapsed / 1000)}s
        </p>
      </div>

      {/*
        O que acontece quando terminar. E a parte que transforma o aviso de
        "algo esta errado" em "aguarde": sem dizer qual e o ganho da espera,
        nao ha motivo para esperar.
      */}
      <p className="rounded-md bg-muted px-3 py-2 text-xs leading-relaxed">
        {t("wakeReady")}
      </p>
    </div>
  );
}

function OfflineContent({ onRetry }: { onRetry: () => void }) {
  const t = useTranslations("app");

  return (
    <div className="flex flex-col gap-3">
      {/*
        Titulos diferentes para situacoes diferentes. Com backend remoto ainda
        estamos tentando, entao "o backend nao esta respondendo" soaria
        definitivo e mandaria a pessoa embora de algo que ainda pode voltar.
      */}
      <p className="text-sm font-semibold">
        {IS_LOCAL_API ? t("backendDownTitle") : t("wakeSlowTitle")}
      </p>

      <p className="text-xs leading-relaxed text-muted-foreground">
        {/*
          `t.rich` substitui TAGS da mensagem, nao argumentos entre chaves. A
          versao anterior usava `{command}` e passava uma funcao - e o
          resultado era vazio: a frase chegava ao usuario como "Inicie com  e
          recarregue esta pagina", sem o comando.
        */}
        {IS_LOCAL_API
          ? t.rich("backendDownBody", {
              command: (chunks) => <code className="font-mono text-[11px]">{chunks}</code>,
            })
          : t("wakeFailedBody")}
      </p>

      <Button variant="outline" size="sm" onClick={onRetry} className="self-start">
        {t("retry")}
      </Button>
    </div>
  );
}
