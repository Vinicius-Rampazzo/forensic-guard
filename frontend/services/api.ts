/**
 * Camada de acesso a API.
 *
 * Regra do projeto: nenhum componente chama `fetch` diretamente. Tudo passa
 * por aqui. O ganho aparece quando a API muda - trocar uma rota, adicionar um
 * cabecalho, mudar o tratamento de erro - porque existe um unico arquivo para
 * editar, em vez de dez componentes.
 */

import type { HealthResponse } from "@/types/api";

/**
 * URL base do backend.
 *
 * O `??` cobre o caso de alguem rodar o projeto sem criar o .env.local.
 * O default aponta para o backend local, entao a aplicacao funciona logo apos
 * o clone, sem configuracao.
 */
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

/**
 * Erro vindo da API.
 *
 * Uma classe propria permite que o componente distinga "a API respondeu com
 * erro" (status HTTP ruim) de "nao consegui nem falar com a API" (backend
 * fora do ar, DNS, CORS) - situacoes que pedem mensagens diferentes.
 */
export class ApiError extends Error {
  constructor(
    message: string,
    readonly status?: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/**
 * Consulta o health check do backend.
 *
 * @param signal permite cancelar a requisicao (usado quando o componente
 *   e desmontado antes da resposta chegar).
 */
export async function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  let response: Response;

  try {
    response = await fetch(`${API_BASE_URL}/health`, {
      signal,
      // Sem cache: a pergunta e "a API esta de pe AGORA?". Uma resposta
      // guardada de dois minutos atras nao responde isso.
      cache: "no-store",
    });
  } catch (error) {
    // fetch so rejeita em falha de rede. Status 404 ou 500 nao caem aqui -
    // eles chegam como uma Response com response.ok === false.
    if (error instanceof Error && error.name === "AbortError") {
      throw error;
    }
    throw new ApiError("Could not reach the API");
  }

  if (!response.ok) {
    throw new ApiError(`API responded with status ${response.status}`, response.status);
  }

  return (await response.json()) as HealthResponse;
}
