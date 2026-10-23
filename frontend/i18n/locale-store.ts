/**
 * Onde o idioma escolhido fica guardado.
 *
 * O idioma vive no localStorage, nao no estado do React. Isso importa porque
 * ele precisa sobreviver a recarga da pagina, e porque assim existe uma unica
 * fonte de verdade - o mesmo raciocinio do tema escuro.
 *
 * Por que useSyncExternalStore e nao useState
 * -------------------------------------------
 * O localStorage e um sistema externo ao React. Copiar o valor dele para
 * dentro de um useState criaria duas fontes que podem divergir, e o lint do
 * React Compiler recusa `setState` dentro de efeito justamente por isso.
 *
 * As funcoes abaixo formam o contrato que `useSyncExternalStore` espera:
 * uma para se inscrever nas mudancas, uma para ler o valor atual, e uma para
 * o valor usado na renderizacao do servidor.
 */

export const LOCALES = ["en", "pt-BR"] as const;

export type Locale = (typeof LOCALES)[number];

export const DEFAULT_LOCALE: Locale = "en";

const STORAGE_KEY = "forensicguard-locale";

/**
 * Evento proprio disparado quando o idioma muda nesta aba.
 *
 * O evento nativo `storage` so dispara em OUTRAS abas - a que fez a mudanca
 * nao e notificada. Sem este evento adicional, trocar o idioma nao
 * re-renderizaria nada.
 */
const CHANGE_EVENT = "forensicguard:locale";

export function subscribeToLocale(onChange: () => void): () => void {
  window.addEventListener(CHANGE_EVENT, onChange);
  window.addEventListener("storage", onChange);

  return () => {
    window.removeEventListener(CHANGE_EVENT, onChange);
    window.removeEventListener("storage", onChange);
  };
}

export function readLocale(): Locale {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);

    if (stored && (LOCALES as readonly string[]).includes(stored)) {
      return stored as Locale;
    }
  } catch {
    // Navegacao anonima ou armazenamento bloqueado.
  }

  return DEFAULT_LOCALE;
}

/**
 * Valor usado na renderizacao do servidor, onde localStorage nao existe.
 *
 * Sempre o idioma padrao. Quem escolheu portugues ve um instante de ingles no
 * primeiro quadro - o preco de guardar a preferencia no localStorage em vez
 * de num cookie, que o servidor conseguiria ler.
 */
export function readServerLocale(): Locale {
  return DEFAULT_LOCALE;
}

export function writeLocale(locale: Locale): void {
  try {
    localStorage.setItem(STORAGE_KEY, locale);
  } catch {
    // O idioma ainda muda nesta sessao, so nao e lembrado na proxima.
  }

  window.dispatchEvent(new Event(CHANGE_EVENT));
}
