/**
 * Estado de saude da API, compartilhado pela aplicacao inteira.
 *
 * Quatro estados, e nao dois
 * --------------------------
 * Enquanto o backend era sempre local, "online ou offline" bastava: ou o
 * processo estava rodando, ou nao estava, e a resposta vinha em
 * milissegundos.
 *
 * Num servidor de plano gratuito existe um terceiro caso, e ele e o mais
 * comum de todos: o servico hiberna depois de um tempo sem uso e leva cerca de
 * um minuto para voltar. Nesse intervalo ele nao esta fora do ar - esta
 * ligando. Chamar isso de "offline" seria a interface mentindo sobre o proprio
 * estado, e mandando a pessoa embora de algo que ia funcionar.
 *
 *   checking -> a primeira resposta ainda nao chegou
 *   waking   -> demorou demais; o servidor esta subindo
 *   online   -> respondeu
 *   offline  -> desistimos, ou o backend local nao esta rodando
 *
 * O estado `waking` so existe quando o backend e remoto. Backend local que nao
 * esta no ar recusa a conexao na hora: nao ha nada subindo, e esperar seria
 * so enrolar quem esqueceu de rodar o servidor.
 *
 * Por que isto e um provider, e nao um hook solto
 * -----------------------------------------------
 * Era um hook, e cada componente que o chamava fazia a propria consulta. Dois
 * consumidores, dois estados independentes - o que parecia inofensivo ate
 * existir um botao "tentar novamente": clicar nele acertava o selo do
 * cabecalho e deixava o aviso da pagina dizendo que a API continuava fora.
 *
 * Com um provider, existe uma consulta e um estado. E, de quebra, acabou a
 * requisicao duplicada que eu tinha justificado como "barata".
 */

"use client";

import {
  type ReactNode,
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";

import { IS_LOCAL_API, getHealth } from "@/services/api";

export type ApiStatus = "checking" | "waking" | "online" | "offline";

interface ApiHealth {
  status: ApiStatus;
  /** Limite de upload informado pelo backend. Null ate a primeira resposta. */
  uploadLimit: number | null;
  /** Instante em que a espera comecou, para desenhar o progresso. */
  wakingSince: number | null;
  retry: () => void;
}

/** Sem resposta depois disto, assumimos que o servidor esta acordando. */
const WAKE_HINT_MS = 2_500;

/** Acima disto a demora deixa de ser esperada e o aviso muda de tom. */
const TOO_SLOW_MS = 90_000;

/** Pausa entre tentativas. O Render responde 502 enquanto o conteiner sobe. */
const RETRY_DELAY_MS = 3_000;

/** Pausa depois que a espera passou do esperado. */
const SLOW_RETRY_MS = 15_000;

const ApiHealthContext = createContext<ApiHealth | null>(null);

export function ApiHealthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<ApiStatus>("checking");
  const [uploadLimit, setUploadLimit] = useState<number | null>(null);
  const [wakingSince, setWakingSince] = useState<number | null>(null);
  const [attempt, setAttempt] = useState(0);

  // O estado volta para o inicio aqui, no manipulador de evento, e nao dentro
  // do efeito. `setState` sincrono dentro de efeito provoca renderizacao em
  // cascata, e o compilador do React recusa - com razao.
  const retry = useCallback(() => {
    setStatus("checking");
    setWakingSince(null);
    setAttempt((value) => value + 1);
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    const startedAt = Date.now();

    // Encerra o laco: ou deu certo, ou o componente saiu de cena, ou nao ha o
    // que esperar (backend local).
    let stopped = false;

    // Passou do tempo esperado. O laco continua, so que mais devagar.
    let slowedDown = false;

    const hint = window.setTimeout(() => {
      if (stopped || IS_LOCAL_API) return;

      setStatus("waking");
      setWakingSince(startedAt);
    }, WAKE_HINT_MS);

    /*
      Com backend remoto, NUNCA paramos de tentar.

      A interface diz que a conexao acontece sozinha, e isso precisa ser
      verdade - texto que promete uma reconexao que nao esta acontecendo e
      exatamente o tipo de afirmacao sem lastro que este projeto nao faz.
      Passado o tempo esperado, o rotulo muda de tom e as tentativas se
      espacam, mas continuam. Se o servidor subir aos cinco minutos, a tela
      fica verde sozinha.

      Com backend local e o oposto: conexao recusada chega em milissegundos,
      nao ha nada subindo, e insistir seria so gastar bateria de quem esqueceu
      de rodar o servidor.
    */
    const tooSlow = window.setTimeout(
      () => {
        if (stopped) return;

        slowedDown = true;
        setStatus("offline");

        if (IS_LOCAL_API) {
          stopped = true;
          controller.abort();
        }
      },
      IS_LOCAL_API ? WAKE_HINT_MS : TOO_SLOW_MS,
    );

    async function probe() {
      while (!stopped) {
        try {
          const health = await getHealth(controller.signal);

          if (stopped) return;

          stopped = true;
          setUploadLimit(health.max_upload_size);
          setStatus("online");
          return;
        } catch {
          if (controller.signal.aborted) return;

          // Nao desiste na primeira falha: um servidor que esta subindo
          // responde erro antes de responder certo.
          await new Promise((resolve) =>
            window.setTimeout(resolve, slowedDown ? SLOW_RETRY_MS : RETRY_DELAY_MS),
          );
        }
      }
    }

    void probe();

    return () => {
      stopped = true;
      window.clearTimeout(hint);
      window.clearTimeout(tooSlow);
      controller.abort();
    };
  }, [attempt]);

  return (
    <ApiHealthContext.Provider value={{ status, uploadLimit, wakingSince, retry }}>
      {children}
    </ApiHealthContext.Provider>
  );
}

export function useApiHealth(): ApiHealth {
  const value = useContext(ApiHealthContext);

  if (value === null) {
    throw new Error("useApiHealth precisa estar dentro de <ApiHealthProvider>");
  }

  return value;
}
