/**
 * Formatadores compartilhados pela interface.
 *
 * Ficam num modulo proprio porque sao usados por componentes que nao tem
 * relacao entre si - o dropzone, a visao geral do arquivo e a lista de
 * anexos. Importar uma funcao de formatacao de dentro de um componente de
 * relatorio funcionaria, mas criaria uma dependencia sem sentido.
 */

/** Converte bytes em texto legivel: 84921 -> "82.9 KB". */
export function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 bytes";

  const units = ["bytes", "KB", "MB", "GB"];
  const exponent = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const value = bytes / 1024 ** exponent;

  return `${exponent === 0 ? value : value.toFixed(1)} ${units[exponent]}`;
}

/** Texto curto explicando o que a entropia observada sugere. */
export function describeEntropy(entropy: number): string {
  if (entropy > 7.5) return "compressed, encrypted or packed";
  if (entropy > 6) return "binary content";
  if (entropy > 3) return "mostly text";
  return "highly repetitive";
}

/** Numero com separador de milhar, no formato en-US usado pela interface. */
export function formatCount(value: number): string {
  return value.toLocaleString("en-US");
}
