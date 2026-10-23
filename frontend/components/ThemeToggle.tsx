/**
 * Alternador entre tema escuro e claro.
 *
 * Escrito a mao em vez de usar a biblioteca `next-themes`. Sao poucas linhas e
 * evita mais uma dependencia - a parte dificil do problema, o flash de tema
 * errado no carregamento, ja esta resolvida pelo script em `app/layout.tsx`.
 *
 * Por que useSyncExternalStore e nao useState
 * -------------------------------------------
 * O tema nao mora no React: ele mora na classe `dark` do elemento <html>, que
 * e quem o CSS consulta. Guardar uma copia disso em useState criaria duas
 * fontes de verdade que podem divergir - e e justamente o que o lint do React
 * Compiler aponta ao recusar `setState` dentro de um efeito.
 *
 * useSyncExternalStore existe para este caso: ler um valor que vive FORA do
 * React e se inscrever nas mudancas dele. Aqui a inscricao e um
 * MutationObserver na classe do <html>, entao se qualquer outro codigo trocar
 * o tema, este botao acompanha sozinho.
 */

"use client";

import { Moon, Sun } from "lucide-react";
import { useSyncExternalStore } from "react";

import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

const STORAGE_KEY = "forensicguard-theme";

/** Avisa o React sempre que a classe do <html> mudar. */
function subscribeToTheme(onChange: () => void): () => void {
  const observer = new MutationObserver(onChange);

  observer.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ["class"],
  });

  return () => observer.disconnect();
}

/** Le o tema atual direto do DOM, que e onde ele de fato vive. */
function readTheme(): boolean {
  return document.documentElement.classList.contains("dark");
}

/**
 * Valor usado na renderizacao do servidor, onde `document` nao existe.
 *
 * O escuro e o padrao da ferramenta, e o `layout.tsx` ja marca a classe no
 * HTML enviado - entao servidor e cliente concordam, e nao ha erro de
 * hidratacao.
 */
function readThemeOnServer(): boolean {
  return true;
}

export function ThemeToggle() {
  const isDark = useSyncExternalStore(subscribeToTheme, readTheme, readThemeOnServer);

  function toggle() {
    const next = !isDark;

    // Escreve no DOM. O MutationObserver acima percebe e o React re-renderiza
    // sozinho - nao ha setState aqui.
    document.documentElement.classList.toggle("dark", next);

    try {
      localStorage.setItem(STORAGE_KEY, next ? "dark" : "light");
    } catch {
      // Navegacao anonima ou armazenamento bloqueado. O tema ainda funciona
      // nesta sessao, so nao e lembrado na proxima.
    }
  }

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          onClick={toggle}
          aria-label="Toggle colour theme"
        >
          {isDark ? <Moon className="size-4" /> : <Sun className="size-4" />}
        </Button>
      </TooltipTrigger>
      <TooltipContent>{isDark ? "Light theme" : "Dark theme"}</TooltipContent>
    </Tooltip>
  );
}
