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
  /**
   * Maior upload aceito, em bytes.
   *
   * Vem do backend em vez de ser repetido aqui por um motivo pratico: o
   * limite e configuravel por variavel de ambiente. Se o frontend tivesse a
   * propria copia do numero, os dois divergiriam no dia em que alguem
   * mudasse a configuracao - e o usuario veria uma mensagem mentindo sobre
   * qual e o limite.
   */
  max_upload_size: number;
}
