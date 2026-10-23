/**
 * Dobra inicial da pagina institucional.
 *
 * Ocupa a janela inteira e responde, antes de qualquer interacao, as tres
 * perguntas de quem chega: o que isto faz, o que recebo de volta, e o que
 * acontece com o meu arquivo.
 *
 * A logo e grande de proposito. E a tela que vai parar nas capturas de tela
 * do portfolio, e uma marca timida nao sustenta uma primeira impressao.
 *
 * Aqui nao entra `motion`. A entrada e a animacao de CSS que ja existia, e nada
 * depende de rolagem: esta e a parte que precisa estar inteira no primeiro
 * quadro, nao aparecendo aos poucos.
 */

"use client";

import { ArrowRight, ChevronDown, Database, HardDrive, UserX } from "lucide-react";
import { useTranslations } from "next-intl";

import { Logo, Wordmark } from "@/components/Logo";
import { ScrambleText } from "@/components/ScrambleText";
import { Button } from "@/components/ui/button";
import { Link } from "@/i18n/navigation";

/**
 * Numeros reais do projeto, exibidos como prova de capacidade.
 *
 * Constantes escritas a mao de proposito: busca-los no backend obrigaria a
 * esperar uma resposta antes de desenhar a tela de entrada, e eles mudam uma
 * vez por etapa, nao a cada analise.
 */
const STATS = [
  { value: "33", key: "formats" as const },
  { value: "16", key: "rules" as const },
  { value: "275", key: "tests" as const },
];

const GUARANTEES = [
  { icon: HardDrive, key: "noUpload" as const },
  { icon: Database, key: "noDatabase" as const },
  { icon: UserX, key: "noAccount" as const },
];

export function LandingScreen() {
  const t = useTranslations("landing");

  return (
    /*
      `svh` e nao `vh`.

      No celular, `100vh` e a altura da janela COM a barra de endereco
      escondida. Rolar para baixo esconde a barra, rolar para cima a traz de
      volta - e a cada troca a altura real da janela muda, esta secao e
      remedida, a pagina inteira muda de tamanho e o conteudo escorrega. E o
      que dava a impressao de a barra de cima estar tremendo.

      `svh` e a altura da janela COM a barra visivel: um valor que nao muda
      durante a rolagem. A secao pode sobrar alguns pixels embaixo quando a
      barra do navegador some, o que e muito melhor que a pagina pulsar.
    */
    <section className="relative flex min-h-[calc(100svh-var(--app-header-height-top))] flex-col items-center justify-center overflow-hidden px-6 py-16">
      <GridBackdrop />

      <div className="fg-rise relative flex flex-col items-center gap-7 text-center">
        <Logo glow animated priority className="size-44 sm:size-56 lg:size-64" />

        <div className="flex flex-col items-center gap-4">
          <Wordmark className="text-3xl sm:text-4xl" />

          {/*
            O titulo e a linha de apoio se decodificam ao carregar. Nao ha
            atraso no titulo: ele e a primeira coisa que a pessoa le, e
            esconde-lo por meio segundo para depois revelar seria cobrar
            espera por um efeito.
          */}
          <h1 className="max-w-2xl text-3xl font-semibold tracking-tight text-balance sm:text-5xl">
            <ScrambleText text={t("headline")} duration={620} />
          </h1>

          <p className="max-w-xl text-sm text-balance text-muted-foreground sm:text-base">
            <ScrambleText text={t("subheadline")} delay={180} />
          </p>
        </div>

        <dl className="flex flex-wrap items-center justify-center gap-x-10 gap-y-4">
          {STATS.map(({ value, key }, index) => (
            <div key={key} className="flex flex-col items-center gap-0.5">
              <dt
                className="font-mono text-3xl font-semibold tabular-nums"
                // Alterna magenta e ciano, acompanhando a divisao da logo.
                style={{
                  color: index % 2 === 0 ? "var(--brand-magenta)" : "var(--brand-cyan)",
                }}
              >
                {value}
              </dt>
              {/*
                O numero fica parado; so o rotulo se decodifica. Embaralhar o
                "33" criaria, por um instante, a impressao de outro numero -
                e numero errado piscando numa ferramenta de pericia e o tipo
                de brincadeira que custa confianca.
              */}
              <dd className="text-[11px] tracking-wider text-muted-foreground uppercase">
                <ScrambleText text={t(key)} delay={320 + index * 70} />
              </dd>
            </div>
          ))}
        </dl>

        {/*
          Agora e um link, nao um botao que troca estado: a analise virou rota
          propria. Isso muda mais do que parece - da para abrir em outra aba,
          copiar o endereco e voltar com o botao do navegador.
        */}
        <Button
          size="lg"
          asChild
          className="group gap-2 border-0 text-base font-semibold transition-all duration-200 hover:brightness-110 active:scale-[0.98]"
          // Ciano solido da logo. O texto vai escuro porque a cor e clara
          // demais para sustentar texto branco com contraste suficiente.
          style={{
            background: "var(--brand-cyan)",
            color: "oklch(0.16 0.02 268)",
            boxShadow: "0 0 28px -8px var(--brand-cyan)",
          }}
        >
          <Link href="/analyze">
            {t("enter")}
            <ArrowRight className="size-4 transition-transform duration-200 group-hover:translate-x-1" />
          </Link>
        </Button>

        <ul className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2">
          {GUARANTEES.map(({ icon: Icon, key }) => (
            <li
              key={key}
              className="flex items-center gap-1.5 text-[11px] text-muted-foreground"
            >
              <Icon className="size-3.5" />
              {t(key)}
            </li>
          ))}
        </ul>

        {/*
          Aviso de que a pagina continua.
          Uma dobra que ocupa a janela inteira nao da nenhuma pista de que
          existe mais coisa embaixo - e quem nao rola nunca ve o resto.
        */}
        <div className="mt-4 flex flex-col items-center gap-1.5 text-muted-foreground">
          <span className="font-mono text-[10px] tracking-[0.2em] uppercase">
            {t("scrollHint")}
          </span>
          <ChevronDown aria-hidden className="fg-cue size-4" />
        </div>
      </div>
    </section>
  );
}

/**
 * Grade de fundo, bem discreta.
 *
 * Desenhada com gradientes repetidos em vez de imagem: nao ha requisicao
 * extra, acompanha o tema pela variavel de cor da borda, e funciona em
 * qualquer resolucao.
 *
 * A mascara radial apaga a grade nas extremidades, para que ela sugira
 * profundidade sem competir com o conteudo.
 */
function GridBackdrop() {
  return (
    <div
      aria-hidden
      className="pointer-events-none absolute inset-0 [mask-image:radial-gradient(ellipse_at_center,black,transparent_70%)] opacity-40"
      style={{
        backgroundImage:
          "linear-gradient(to right, var(--border) 1px, transparent 1px)," +
          "linear-gradient(to bottom, var(--border) 1px, transparent 1px)",
        backgroundSize: "56px 56px",
      }}
    />
  );
}
