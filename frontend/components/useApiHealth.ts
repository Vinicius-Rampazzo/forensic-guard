/**
 * Pergunta ao backend se ele esta de pe, e qual e o limite de upload.
 *
 * Extraido da pagina porque agora ha dois lugares interessados: o cabecalho,
 * que avisa quando a API esta fora, e a bancada de analise, que precisa do
 * limite de tamanho para checar o arquivo antes de enviar.
 *
 * Sim, isso faz duas chamadas a `/health` por carregamento. E de proposito:
 * um cache compartilhado entre componentes resolveria um custo que, numa
 * requisicao para a propria maquina, e de milissegundos - e traria um estado
 * global para ser explicado depois.
 */

"use client";

import { useEffect, useState } from "react";

import { getHealth } from "@/services/api";

export type ApiStatus = "checking" | "online" | "offline";

export function useApiHealth() {
  const [status, setStatus] = useState<ApiStatus>("checking");

  // Null enquanto a checagem nao respondeu. Nesse caso nao ha como validar o
  // tamanho antes de enviar, e o servidor continua sendo a ultima palavra.
  const [uploadLimit, setUploadLimit] = useState<number | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    getHealth(controller.signal)
      .then((health) => {
        setStatus("online");
        setUploadLimit(health.max_upload_size);
      })
      .catch((error: unknown) => {
        if (error instanceof Error && error.name === "AbortError") return;
        setStatus("offline");
      });

    return () => controller.abort();
  }, []);

  return { status, uploadLimit };
}
