/**
 * Secoes institucionais da pagina inicial.
 *
 * Respondem, em ordem, as perguntas de quem chegou e ficou interessado: como
 * funciona, o que exatamente e detectado, como e o resultado, por que e seguro
 * mandar um arquivo suspeito, e o que a ferramenta nao faz.
 *
 * Animacao com `motion`
 * ---------------------
 * O hook caseiro de IntersectionObserver saiu daqui. Ele resolvia uma coisa -
 * revelar ao entrar na tela - e estas secoes precisam de tres: revelar,
 * escalonar os itens de uma fileira, e reagir ao ponteiro.
 *
 * O padrao usado e o de variantes: o elemento pai declara `hidden` e `shown`,
 * e os filhos que tambem tem variantes herdam esse estado automaticamente.
 * Isso permite escrever "esta fileira entra em cascata" sem calcular atraso
 * nenhum a mao, e e o que `staggerChildren` faz.
 *
 * `MotionConfig reducedMotion="user"` cobre quem pediu menos movimento no
 * sistema operacional: a biblioteca passa a animar so opacidade e descarta
 * deslocamento e escala, sem precisar de condicional em lugar nenhum.
 */

"use client";

import {
  Binary,
  Fingerprint,
  FileSearch,
  Gauge,
  Image as ImageIcon,
  Link2,
  Lock,
  Mail,
  Scan,
  ScrollText,
  ShieldOff,
  Terminal,
  type LucideIcon,
} from "lucide-react";
import {
  MotionConfig,
  motion,
  useMotionTemplate,
  useMotionValue,
  type Variants,
} from "motion/react";
import { useTranslations } from "next-intl";
import type { CSSProperties, PointerEvent, ReactNode } from "react";

import { ScrambleText } from "@/components/ScrambleText";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

/**
 * Curva de aceleracao da entrada.
 *
 * Comeca rapido e desacelera no fim, o oposto de uma transicao linear. E o que
 * faz o movimento parecer que tem peso em vez de parecer um slide de
 * apresentacao.
 */
const EASE: [number, number, number, number] = [0.16, 1, 0.3, 1];

/** Pai que escalona a entrada dos filhos. */
const CONTAINER: Variants = {
  hidden: {},
  shown: { transition: { staggerChildren: 0.08 } },
};

/** Versao rapida, para as linhas do terminal "sendo impressas". */
const CONTAINER_FAST: Variants = {
  hidden: {},
  shown: { transition: { staggerChildren: 0.055, delayChildren: 0.15 } },
};

/** Filho que sobe e aparece. */
const ITEM: Variants = {
  hidden: { opacity: 0, y: 24 },
  shown: { opacity: 1, y: 0, transition: { duration: 0.55, ease: EASE } },
};

/** Linha de terminal: so opacidade, para parecer texto surgindo. */
const LINE: Variants = {
  hidden: { opacity: 0 },
  shown: { opacity: 1, transition: { duration: 0.18 } },
};

/**
 * Secao que dispara a cascata quando entra na tela.
 *
 * `once: true` porque a animacao de entrada roda uma vez. Conteudo que aparece
 * e some conforme a rolagem sobe e desce e cansativo, e atrapalha quem volta
 * para reler algo.
 *
 * `margin` negativo adia o disparo: o bloco so conta como visivel depois de
 * ter entrado de verdade, e nao no instante em que a borda de cima dele
 * encosta na borda de baixo da janela.
 */
function Section({ children }: { children: ReactNode }) {
  return (
    <motion.section
      // `data-reveal` nao faz nada no navegador comum. Existe para o bloco
      // <noscript> do layout poder desfazer a opacidade zero quando o
      // JavaScript nao carrega - senao o institucional ficaria invisivel.
      data-reveal
      className="flex flex-col gap-10"
      variants={CONTAINER}
      initial="hidden"
      whileInView="shown"
      viewport={{ once: true, margin: "-80px" }}
    >
      {children}
    </motion.section>
  );
}

function SectionTitle({ children }: { children: string }) {
  return (
    <motion.h2
      variants={ITEM}
      className="mx-auto max-w-2xl text-center text-2xl font-semibold tracking-tight text-balance sm:text-3xl"
    >
      <ScrambleText text={children} duration={620} />
    </motion.h2>
  );
}

/**
 * Cartao com um foco de luz que segue o ponteiro.
 *
 * A posicao do ponteiro vai para dois `MotionValue`, que o `motion` escreve
 * direto no estilo do elemento sem passar pelo React. E a diferenca entre um
 * efeito fluido e um que re-renderiza o componente a cada pixel de movimento
 * do mouse.
 */
function SpotlightCard({
  accent,
  beam = false,
  beamDelay = "0s",
  children,
}: {
  accent: string;
  /** Liga a luz que percorre a borda. Ver `.fg-beam` em globals.css. */
  beam?: boolean;
  beamDelay?: string;
  children: ReactNode;
}) {
  const x = useMotionValue(0);
  const y = useMotionValue(0);

  const background = useMotionTemplate`radial-gradient(280px circle at ${x}px ${y}px, color-mix(in oklab, ${accent} 16%, transparent), transparent 72%)`;

  function handlePointerMove(event: PointerEvent<HTMLDivElement>) {
    const bounds = event.currentTarget.getBoundingClientRect();

    x.set(event.clientX - bounds.left);
    y.set(event.clientY - bounds.top);
  }

  return (
    <motion.div variants={ITEM} onPointerMove={handlePointerMove} className="group h-full">
      <Card
        className={cn("fg-card relative h-full overflow-hidden", beam && "fg-beam")}
        // Propriedade customizada lida pelo `animation-delay` do ::after. Nao
        // da para aplicar estilo inline num pseudo-elemento; a variavel e a
        // ponte entre o JSX e ele.
        style={{ "--fg-beam-delay": beamDelay } as CSSProperties}
      >
        {/*
          Precisa ser `motion.div`, e nao `div`: o valor de `background` e um
          MotionValue, e so o motion sabe escrever isso no estilo sem passar
          pelo React. Num `div` comum o TypeScript recusa, e com razao.
        */}
        <motion.div
          aria-hidden
          className="pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-300 group-hover:opacity-100"
          // O gradiente vive numa camada propria para poder aparecer e
          // desaparecer sem levar o conteudo do cartao junto.
          style={{ background }}
        />
        {children}
      </Card>
    </motion.div>
  );
}

/* -------------------------------------------------------------------------- */

const PIPELINE: { icon: LucideIcon; key: string }[] = [
  { icon: Fingerprint, key: "hash" },
  { icon: Gauge, key: "entropy" },
  { icon: Scan, key: "signature" },
  { icon: ScrollText, key: "strings" },
  { icon: Terminal, key: "score" },
];

/*
  As cores aqui sao as variantes "de tinta", nao as puras da logo. O ciano
  puro sobre o fundo branco do tema claro desaparece - e os pontinhos da lista
  e o icone sumiriam junto.
*/
const EVIDENCE: { icon: LucideIcon; key: string; accent: string }[] = [
  { icon: FileSearch, key: "file", accent: "var(--brand-magenta-ink)" },
  { icon: ImageIcon, key: "image", accent: "var(--brand-cyan-ink)" },
  { icon: Mail, key: "email", accent: "var(--brand-magenta-ink)" },
  { icon: Link2, key: "url", accent: "var(--brand-cyan-ink)" },
];

const GUARANTEES: { icon: LucideIcon; key: string }[] = [
  { icon: Lock, key: "local" },
  { icon: ShieldOff, key: "noExecution" },
  { icon: Binary, key: "noNetwork" },
];

export function LandingSections() {
  const t = useTranslations("sections");

  return (
    <MotionConfig reducedMotion="user">
      <div className="flex flex-col gap-28 pb-28">
        {/* ---------------------------------------------------------------- */}
        {/* Como funciona                                                    */}
        {/* ---------------------------------------------------------------- */}
        <Section>
          <SectionTitle>{t("pipelineTitle")}</SectionTitle>

          <motion.div
            variants={CONTAINER}
            className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5"
          >
            {PIPELINE.map(({ icon: Icon, key }, index) => (
              <motion.div key={key} variants={ITEM}>
                <Card className="fg-card fg-edge relative h-full gap-0 overflow-hidden py-5">
                  <CardContent className="flex h-full flex-col gap-2 px-4">
                    <div className="flex items-center justify-between">
                      <Icon className="size-4 text-muted-foreground" />
                      <span className="font-mono text-[10px] text-muted-foreground/60">
                        {String(index + 1).padStart(2, "0")}
                      </span>
                    </div>
                    {/*
                      O titulo se decodifica ao entrar na tela. Em fonte
                      monoespacada porque o ruido troca caractere por
                      caractere: com fonte de largura variavel a palavra
                      mudaria de tamanho a cada quadro.
                    */}
                    {/*
                      O atraso acompanha a entrada em cascata dos cartoes: a
                      decodificacao de cada um comeca quando ele chega, e nao
                      os cinco de uma vez.
                    */}
                    <h3 className="font-mono text-sm font-medium">
                      <ScrambleText text={t(`${key}Title`)} delay={index * 70} />
                    </h3>
                    <p className="text-xs leading-relaxed text-muted-foreground">
                      <ScrambleText text={t(`${key}Body`)} delay={index * 70 + 160} />
                    </p>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </motion.div>
        </Section>

        {/* ---------------------------------------------------------------- */}
        {/* O que e detectado                                                */}
        {/* ---------------------------------------------------------------- */}
        <Section>
          <SectionTitle>{t("detectTitle")}</SectionTitle>

          <motion.div variants={CONTAINER} className="grid gap-4 sm:grid-cols-2">
            {EVIDENCE.map(({ icon: Icon, key, accent }, index) => (
              <SpotlightCard key={key} accent={accent}>
                <CardContent className="relative flex flex-col gap-3">
                  <div className="flex items-center gap-2">
                    <Icon className="size-4" style={{ color: accent }} />
                    <h3 className="text-sm font-medium">
                      <ScrambleText text={t(`${key}Title`)} delay={index * 70} />
                    </h3>
                  </div>
                  <ul className="flex flex-col gap-1.5">
                    {/*
                      A chave usa o indice, nao o texto. Duas linhas iguais na
                      mesma lista sao plausiveis numa traducao, e o React
                      reclamaria de chave repetida - erro que nao aparece em
                      teste, so no console de quem usa.
                    */}
                    {t(`${key}Items`)
                      .split("|")
                      .map((item, itemIndex) => (
                        <li
                          key={itemIndex}
                          className="flex items-start gap-2 text-xs text-muted-foreground"
                        >
                          <span
                            aria-hidden
                            className="mt-1.5 size-1 shrink-0 rounded-full"
                            style={{ background: accent }}
                          />
                          {item}
                        </li>
                      ))}
                  </ul>
                </CardContent>
              </SpotlightCard>
            ))}
          </motion.div>
        </Section>

        {/* ---------------------------------------------------------------- */}
        {/* Exemplo de saida                                                 */}
        {/* ---------------------------------------------------------------- */}
        <Section>
          <SectionTitle>{t("exampleTitle")}</SectionTitle>
          <TerminalExample />
        </Section>

        {/* ---------------------------------------------------------------- */}
        {/* Garantias                                                        */}
        {/* ---------------------------------------------------------------- */}
        <Section>
          <SectionTitle>{t("safetyTitle")}</SectionTitle>

          <motion.div variants={CONTAINER} className="grid gap-4 lg:grid-cols-3">
            {GUARANTEES.map(({ icon: Icon, key }, index) => (
              <SpotlightCard
                key={key}
                accent="var(--brand-cyan-ink)"
                beam
                // Atraso negativo: cada cartao ja comeca com a luz em outro
                // ponto da volta, em vez de os tres piscarem juntos.
                beamDelay={`${index * -2}s`}
              >
                <CardContent className="relative flex flex-col gap-2">
                  <Icon className="size-4" style={{ color: "var(--brand-cyan-ink)" }} />
                  <h3 className="text-sm font-medium">
                    <ScrambleText text={t(`${key}Title`)} delay={index * 70} />
                  </h3>
                  <p className="text-xs leading-relaxed text-muted-foreground">
                    <ScrambleText text={t(`${key}Body`)} delay={index * 70 + 160} />
                  </p>
                </CardContent>
              </SpotlightCard>
            ))}
          </motion.div>
        </Section>

        {/* ---------------------------------------------------------------- */}
        {/* O que a ferramenta NAO faz                                       */}
        {/* ---------------------------------------------------------------- */}
        {/*
          Esta secao e a unica sem moldura, e de proposito.

          Todas as anteriores sao cartao: blocos fechados, alinhados ao centro,
          com borda. Fechar a pagina com mais um deles faria o texto mais
          importante do institucional - o que a ferramenta NAO faz - parecer
          apenas o sexto quadradinho da lista.

          Sem caixa, alinhado a esquerda e com medida de leitura larga, ele le
          como declaracao, que e o que e. O fio vertical substitui a borda:
          delimita sem encaixotar.
        */}
        <Section>
          <motion.div variants={ITEM} className="relative max-w-4xl pl-6 sm:pl-8">
            <span
              aria-hidden
              className="absolute top-1 bottom-1 left-0 w-px"
              style={{
                background:
                  "linear-gradient(to bottom, var(--brand-magenta-ink), transparent)",
              }}
            />

            <h2 className="text-2xl font-semibold tracking-tight text-balance sm:text-3xl">
              <ScrambleText text={t("limitsTitle")} duration={620} />
            </h2>

            <p className="mt-5 text-base leading-relaxed text-muted-foreground sm:text-lg">
              <ScrambleText text={t("limitsBody")} delay={200} duration={700} />
            </p>

            {/*
              Os itens sao escritos como comentario de codigo. `//` marca a
              linha que o programa ignora - exatamente o que esta lista
              enumera. E um sinal que quem le codigo reconhece de imediato,
              sem precisar de icone nem de legenda.

              `columns` em vez de `grid`: o texto flui de uma coluna para a
              outra como prosa, em vez de ocupar celulas de tamanho fixo.
            */}
            <motion.ul
              variants={CONTAINER_FAST}
              className="mt-8 columns-1 gap-x-12 sm:columns-2"
            >
              {t("limitsItems")
                .split("|")
                .map((item, index) => (
                  <motion.li
                    key={index}
                    variants={LINE}
                    className="mb-2.5 break-inside-avoid font-mono text-xs leading-relaxed text-muted-foreground/80"
                  >
                    <span aria-hidden style={{ color: "var(--brand-magenta-ink)" }}>
                      {"// "}
                    </span>
                    {item}
                  </motion.li>
                ))}
            </motion.ul>
          </motion.div>
        </Section>
      </div>
    </MotionConfig>
  );
}

/**
 * Exemplo de relatorio, desenhado como saida de terminal.
 *
 * As linhas aparecem uma a uma, como texto sendo impresso. E o unico lugar da
 * pagina onde o escalonamento tem significado e nao so enfeite: a ordem em que
 * as linhas surgem e a ordem em que a analise de fato acontece.
 *
 * Os numeros sao os de uma analise real: um executavel renomeado para .jpg
 * soma 35 pelo mismatch de extensao e 50 por ser executavel disfarcado.
 * Inventar valores aqui seria ensinar errado a quem le.
 */
function TerminalExample() {
  const t = useTranslations("sections");

  const lines: { text: string; tone?: "dim" | "magenta" | "cyan" | "alert" }[] = [
    { text: "$ forensicguard analyse invoice.jpg", tone: "dim" },
    { text: "" },
    { text: "  sha256    7a467a30ee59de80e7d4b384581e192ee5111b48...", tone: "dim" },
    { text: "  entropy   5.1161 / 8.00", tone: "dim" },
    { text: "  declared  .jpg", tone: "cyan" },
    { text: "  detected  Windows executable (PE / MZ)", tone: "magenta" },
    { text: "" },
    { text: "  RISK 85/100  CRITICAL", tone: "alert" },
    { text: "    +50  executable disguised as another file type" },
    { text: "    +35  extension does not match the detected signature" },
  ];

  const toneClass = {
    dim: "text-muted-foreground",
    alert: "font-semibold text-red-500",
  } as const;

  return (
    <motion.div variants={ITEM} className="overflow-hidden rounded-xl border bg-card">
      {/* Barra de janela, para o bloco ler como terminal e nao como citacao. */}
      <div className="flex items-center gap-2 border-b px-4 py-2.5">
        <span className="size-2.5 rounded-full bg-red-500/70" />
        <span className="size-2.5 rounded-full bg-amber-500/70" />
        <span className="size-2.5 rounded-full bg-emerald-500/70" />
        <span className="ml-2 font-mono text-[11px] text-muted-foreground">
          {t("exampleCaption")}
        </span>
      </div>

      <motion.pre
        variants={CONTAINER_FAST}
        className="overflow-x-auto px-4 py-4 font-mono text-[11px] leading-relaxed sm:text-xs"
      >
        {lines.map((line, index) => (
          <motion.div
            key={index}
            variants={LINE}
            className={cn(
              line.tone === "dim" && toneClass.dim,
              line.tone === "alert" && toneClass.alert,
            )}
            style={
              line.tone === "magenta"
                ? { color: "var(--brand-magenta)" }
                : line.tone === "cyan"
                  ? { color: "var(--brand-cyan)" }
                  : undefined
            }
          >
            {line.text || " "}
          </motion.div>
        ))}

        {/* Prompt vazio com cursor piscando: fecha o bloco como um terminal
            que acabou e esta esperando o proximo comando. */}
        <motion.div variants={LINE} aria-hidden className="mt-3 text-muted-foreground">
          {"$ "}
          <span className="fg-caret">▍</span>
        </motion.div>
      </motion.pre>
    </motion.div>
  );
}
