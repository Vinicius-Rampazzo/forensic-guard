/**
 * Marca do ForensicGuard.
 *
 * O PNG tem fundo transparente de verdade - o preto original foi removido
 * convertendo luminosidade em canal alfa. Por isso ela funciona nos dois
 * temas sem truque de mesclagem, e as bordas suavizadas da arte continuam
 * suaves em vez de serrilhadas.
 *
 * O `priority` existe porque a logo aparece acima da dobra na tela de
 * entrada; sem ele o Next adiaria o carregamento e ela apareceria depois do
 * texto.
 */

import Image from "next/image";

import { cn } from "@/lib/utils";

interface LogoProps {
  className?: string;
  /** Pulsa suavemente. Usado na tela de entrada e durante a analise. */
  animated?: boolean;
  priority?: boolean;
  /** Brilho colorido por tras, para a tela de entrada. */
  glow?: boolean;
}

export function Logo({
  className,
  animated = false,
  priority = false,
  glow = false,
}: LogoProps) {
  return (
    <span
      className={cn(
        "relative inline-block aspect-square shrink-0 select-none",
        animated && "fg-pulse",
        className,
      )}
    >
      {glow && (
        <>
          {/*
            Dois halos desfocados nas cores da marca, posicionados atras da
            arte. Reproduzem a divisao da propria logo - magenta a esquerda,
            ciano a direita - e dao profundidade sem precisar de imagem extra.
          */}
          <span
            aria-hidden
            className="absolute top-1/4 -left-6 size-2/3 rounded-full opacity-25 blur-3xl"
            style={{ background: "var(--brand-magenta)" }}
          />
          <span
            aria-hidden
            className="absolute top-1/4 -right-6 size-2/3 rounded-full opacity-25 blur-3xl"
            style={{ background: "var(--brand-cyan)" }}
          />
        </>
      )}

      <Image
        src="/logo.png"
        alt="ForensicGuard"
        fill
        sizes="(max-width: 640px) 220px, 420px"
        priority={priority}
        className="relative object-contain"
      />
    </span>
  );
}

/**
 * O nome da marca com as cores da logo: Forensic em magenta, Guard em ciano.
 *
 * Componente proprio porque aparece em tres lugares - cabecalho, tela de
 * entrada e relatorio HTML exportado - e repetir os dois <span> coloridos em
 * cada um deles convidaria a divergencia.
 */
export function Wordmark({ className }: { className?: string }) {
  return (
    <span className={cn("font-mono font-semibold tracking-tight", className)}>
      <span style={{ color: "var(--brand-magenta)" }}>Forensic</span>
      <span style={{ color: "var(--brand-cyan)" }}>Guard</span>
    </span>
  );
}
