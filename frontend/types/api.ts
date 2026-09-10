/**
 * Tipos que espelham o contrato da API.
 *
 * Cada interface aqui corresponde a um schema Pydantic do backend. Manter os
 * dois lados alinhados e responsabilidade nossa: o TypeScript nao consegue
 * verificar sozinho se o backend mudou. Por isso os tipos vivem isolados neste
 * arquivo, e nao espalhados pelos componentes - quando a API mudar, existe um
 * unico lugar para atualizar.
 *
 * Backend equivalente: backend/app/schemas/
 */

/** Resposta de GET /health. Espelha `HealthResponse` em schemas/health.py. */
export interface HealthResponse {
  status: string;
  app: string;
  version: string;
}
