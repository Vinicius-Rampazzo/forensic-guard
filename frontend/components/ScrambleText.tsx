/**
 * Texto que se monta como se estivesse sendo decodificado.
 *
 * A palavra aparece como ruido hexadecimal e vai se resolvendo da esquerda
 * para a direita. Nao e so "entrar bonito": diz, sem escrever, que o assunto
 * ali e ler bytes que nao foram feitos para humanos.
 *
 * Um unico laco para a pagina inteira
 * -----------------------------------
 * A primeira versao dava a cada texto o seu proprio `setInterval`, e cada
 * quadro chamava `setState`. Com um titulo isso e irrelevante. Com os sessenta
 * e poucos titulos e subtitulos da pagina inicial seriam sessenta timers
 * disparando sessenta re-renderizacoes do React a cada 30ms - a pagina
 * engasgaria enquanto exibe uma animacao de enfeite.
 *
 * Aqui existe um `requestAnimationFrame` so, compartilhado, que escreve
 * `textContent` direto nos elementos. O React nao participa: nenhum estado
 * muda, nenhum componente re-renderiza. E o mesmo raciocinio do MotionValue
 * nos cartoes - texto que muda sessenta vezes por segundo e aparencia, e
 * aparencia nao precisa passar pelo React.
 *
 * Tres cuidados que o efeito exige
 * --------------------------------
 * 1. O JSX contem o texto CERTO, sempre. O HTML vem pronto do servidor, e se a
 *    primeira renderizacao do cliente mostrasse outra coisa o React acusaria
 *    divergencia de hidratacao. O ruido so e escrito depois, por fora.
 *
 * 2. O texto aparece UMA vez no documento. A tentacao e manter duas copias -
 *    uma `sr-only` com o texto real e outra `aria-hidden` com o ruido - mas
 *    isso escreveria cada titulo duas vezes no HTML, e um <h1> com a frase
 *    repetida e exatamente o que nao se quer entregar a um buscador.
 *
 *    O preco e pequeno: o elemento nao e uma regiao `aria-live`, entao leitor
 *    de tela nao re-anuncia o que muda nele. Ele le o que estiver ali quando
 *    o usuario chegar - e meio segundo depois ali esta o texto certo.
 *
 * 3. A caixa do texto nao pode mudar de tamanho. O alfabeto hexadecimal e o
 *    `tabular-nums` aproximam as larguras, mas nao resolvem: letra nenhuma tem
 *    largura identica a um digito numa fonte proporcional, e basta uma palavra
 *    embaralhada ficar larga demais para o texto quebrar numa linha a mais - e
 *    ai o cartao inteiro muda de altura no meio da animacao.
 *
 *    A solucao e travar a caixa. Mede-se o elemento com o texto REAL (que e o
 *    que esta no DOM antes de tudo comecar), fixa-se largura e altura, e so
 *    entao o ruido entra. Ao terminar, a trava sai. Como a medida veio do
 *    texto final, o antes e o depois sao identicos por construcao - nada se
 *    move em momento nenhum.
 */

"use client";

import { useInView } from "motion/react";
import { useEffect, useRef } from "react";

import { cn } from "@/lib/utils";

/**
 * Alfabeto do ruido: hexadecimal puro.
 *
 * E o que de fato aparece num dump de bytes, entao a escolha e tematica e nao
 * decorativa. Tambem e a que menos mexe na largura do texto - simbolos como
 * `|` e `#` sao estreitos e largos demais, e faziam a linha tremer.
 */
const GLYPHS = "0123456789ABCDEF";

/** Quanto tempo uma palavra leva para se resolver, em milissegundos. */
const DEFAULT_DURATION = 520;

/**
 * ~30 quadros por segundo.
 *
 * Em 60 o ruido vira cintilacao, e o dobro de escritas no DOM nao melhora
 * nada que o olho perceba.
 */
const FRAME_INTERVAL = 33;

interface Job {
  node: HTMLElement;
  text: string;
  startAt: number;
  endAt: number;
}

const jobs = new Set<Job>();

let frameId: number | null = null;
let lastPaint = 0;

function randomGlyph(): string {
  return GLYPHS[(Math.random() * GLYPHS.length) | 0];
}

/**
 * Congela a caixa do elemento no tamanho que o texto real ocupa.
 *
 * Devolve `false` quando o elemento ainda nao foi desenhado (largura ou altura
 * zero) - nesse caso nao ha o que medir, e e melhor nao animar do que animar
 * com uma medida errada.
 */
function lockBox(node: HTMLElement): boolean {
  // `inline-block` ANTES de medir, por dois motivos. Primeiro: um <span> em
  // fluxo normal e inline, e elemento inline simplesmente ignora width e
  // height. Segundo: a altura de uma caixa inline vem das metricas da fonte,
  // nao da entrelinha - medir antes da troca daria um valor menor que o real
  // e cortaria a ultima linha.
  node.style.display = "inline-block";
  node.style.verticalAlign = "top";

  const { width, height } = node.getBoundingClientRect();

  if (width === 0 || height === 0) {
    unlockBox(node);
    return false;
  }

  node.style.width = `${width}px`;
  node.style.height = `${height}px`;

  // Rede de seguranca: se o ruido ainda assim quebrar numa linha a mais, ele e
  // cortado em vez de empurrar o layout. Meio segundo de texto aparado e menos
  // ruim que um cartao pulando de altura.
  node.style.overflow = "hidden";

  return true;
}

function unlockBox(node: HTMLElement) {
  node.style.display = "";
  node.style.verticalAlign = "";
  node.style.width = "";
  node.style.height = "";
  node.style.overflow = "";
}

function paint(now: number) {
  if (now - lastPaint >= FRAME_INTERVAL) {
    lastPaint = now;

    for (const job of jobs) {
      // Ainda no atraso: o texto continua como esta ate a vez dele chegar.
      if (now < job.startAt) continue;

      const progress = (now - job.startAt) / (job.endAt - job.startAt);

      if (progress >= 1) {
        job.node.textContent = job.text;
        unlockBox(job.node);
        jobs.delete(job);
        continue;
      }

      // A duracao e por TEXTO, nao por caractere. Um titulo curto e um
      // paragrafo levam o mesmo tempo - do contrario o paragrafo ficaria
      // embaralhado tempo demais para ser tolerado.
      const settled = Math.floor(progress * job.text.length);

      // Revela no mesmo quadro em que o ruido e escrito, nunca antes. Ate
      // aqui o elemento estava invisivel pela classe `fg-scramble`, entao o
      // texto limpo nao chega a aparecer na frente do efeito.
      job.node.style.visibility = "visible";

      job.node.textContent =
        job.text.slice(0, settled) + job.text.slice(settled).replace(/\S/g, randomGlyph);
    }
  }

  frameId = jobs.size > 0 ? requestAnimationFrame(paint) : null;
}

function schedule(job: Job) {
  jobs.add(job);

  if (frameId === null) {
    frameId = requestAnimationFrame(paint);
  }
}

interface ScrambleTextProps {
  text: string;
  /** Atraso antes de comecar, para escalonar varios textos de uma fileira. */
  delay?: number;
  duration?: number;
  className?: string;
}

export function ScrambleText({
  text,
  delay = 0,
  duration = DEFAULT_DURATION,
  className,
}: ScrambleTextProps) {
  const ref = useRef<HTMLSpanElement>(null);

  // `once: true` porque a decodificacao roda uma vez. Repetir a cada rolagem
  // transformaria a pagina num letreiro.
  const inView = useInView(ref, { once: true, margin: "-40px" });

  useEffect(() => {
    const node = ref.current;

    if (!node || !inView) return;

    // Quem pediu menos movimento recebe o texto parado. Este efeito e
    // especialmente agressivo para quem tem sensibilidade a movimento, porque
    // o ruido muda em cada quadro.
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    let job: Job | null = null;

    // Comeca imediatamente, sem esperar nada.
    //
    // A versao anterior esperava `document.fonts.ready` para medir a caixa com
    // a fonte definitiva. Boa intencao, resultado ruim: essa promessa so
    // resolve quando o documento TERMINA de carregar, imagens inclusive - e a
    // logo e um PNG grande. Na pratica o efeito so comecava bem depois de a
    // pagina estar pronta, o que parecia defeito.
    //
    // O risco que aquela espera cobria e pequeno: se a fonte trocar no meio da
    // animacao, a caixa travada fica alguns pixels errada por meio segundo, e
    // o `overflow: hidden` apara o excesso. Ao terminar, a trava sai e o texto
    // final e sempre medido pelo proprio navegador.
    if (lockBox(node)) {
      const startAt = performance.now() + delay;
      const scheduled: Job = { node, text, startAt, endAt: startAt + duration };

      job = scheduled;
      schedule(scheduled);
    } else {
      // Nao deu para medir: nao ha animacao, mas o texto precisa aparecer.
      node.style.visibility = "visible";
    }

    return () => {
      // Sai do laco, devolve o texto certo e solta a caixa. Sem isto, um
      // componente desmontado no meio da animacao deixaria ruido congelado na
      // tela, com largura e altura fixas, caso voltasse a ser montado.
      const scheduled = job;

      if (scheduled) jobs.delete(scheduled);

      node.textContent = text;
      unlockBox(node);

      // Visibilidade por ultimo e sempre: a classe `fg-scramble` esconde por
      // padrao, entao um elemento que saia daqui sem isto ficaria invisivel.
      node.style.visibility = "visible";
    };
  }, [inView, text, delay, duration]);

  return (
    <span ref={ref} className={cn("fg-scramble tabular-nums", className)}>
      {text}
    </span>
  );
}
