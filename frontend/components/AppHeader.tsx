/**
 * Barra de cima, compartilhada pelas duas rotas.
 *
 * Vive no layout, nao nas paginas. Por isso ela nao recebe mais nada por
 * propriedade: descobre sozinha o estado da API e, pelo caminho atual, se faz
 * sentido mostrar o atalho para a analise.
 *
 * Ela e alta e transparente no topo da pagina, e encolhe ganhando fundo e
 * borda assim que a rolagem comeca. Quem esta chegando ve a marca com
 * destaque; quem ja esta lendo recupera a altura da tela.
 */

"use client";

import { useTranslations } from "next-intl";
import { useEffect, useRef } from "react";

import { ApiStatusBadge } from "@/components/ApiStatusBadge";
import { LanguageToggle } from "@/components/LanguageToggle";
import { Logo, Wordmark } from "@/components/Logo";
import { ThemeToggle } from "@/components/ThemeToggle";
import { useApiHealth } from "@/components/ApiHealthProvider";
import { Button } from "@/components/ui/button";
import { Link, usePathname } from "@/i18n/navigation";

export function AppHeader() {
  const t = useTranslations("app");

  /*
    A consulta roda em TODAS as rotas, mesmo onde o selo nao aparece.

    Nao e desperdicio, e o contrario: num servidor que hiberna, a requisicao
    feita ao abrir o institucional ja comeca a acordar o backend. Enquanto a
    pessoa le a pagina, ele sobe - e quando ela clica em "Iniciar analise", na
    maioria das vezes ja esta pronto. A espera acontece no tempo de leitura,
    que e tempo que ela ia gastar de qualquer jeito.
  */
  const { status, wakingSince, retry } = useApiHealth();

  // `usePathname` do next-intl devolve o caminho SEM o prefixo de idioma, por
  // isso a comparacao e com "/analyze" e nao com "/pt-br/analyze".
  const pathname = usePathname();

  const ref = useRef<HTMLElement>(null);

  useEffect(() => {
    const header = ref.current;

    if (!header) return;

    /*
      O estado vai para um atributo no DOM, nao para o estado do React. Rolar
      dispara dezenas de eventos por segundo, e cada `setState` seria uma
      re-renderizacao da barra inteira para mudar duas classes.

      Dois limiares diferentes, e nao um so - isso se chama histerese. A barra
      ocupa espaco no fluxo, entao encolher sobe o conteudo que vem depois. Com
      um unico limiar, uma rolagem parada exatamente em cima dele poderia
      alternar sem parar entre os dois tamanhos. Com a volta mais baixa que a
      ida, sair de um estado exige um movimento deliberado.
    */
    let scrolled = false;

    const sync = () => {
      const y = window.scrollY;
      const next = scrolled ? y > 8 : y > 24;

      if (next === scrolled) return;

      scrolled = next;
      header.dataset.scrolled = String(next);
    };

    // Uma vez na montagem: o navegador restaura a posicao da rolagem ao
    // voltar para uma pagina, e a barra precisa nascer no estado certo.
    sync();

    // `passive` avisa ao navegador que este ouvinte nunca vai cancelar a
    // rolagem, o que permite rolar sem esperar o JavaScript responder.
    window.addEventListener("scroll", sync, { passive: true });

    return () => window.removeEventListener("scroll", sync);
  }, []);

  return (
    <header
      ref={ref}
      data-scrolled="false"
      className="group sticky top-0 z-20 border-b border-transparent backdrop-blur transition-[background-color,border-color,box-shadow] duration-300 ease-fg data-[scrolled=true]:border-border data-[scrolled=true]:bg-background/80 data-[scrolled=true]:shadow-sm"
    >
      {/*
        Altura fixa em vez de padding: o que gruda na rolagem mais abaixo
        precisa saber exatamente onde esta barra termina. O par destas duas
        alturas sao as variaveis `--app-header-height*` em globals.css.
      */}
      <div className="mx-auto flex h-[var(--app-header-height-top)] w-full max-w-6xl items-center gap-4 px-6 transition-[height] duration-300 ease-fg group-data-[scrolled=true]:h-[var(--app-header-height)]">
        {/*
          A marca leva de volta ao institucional. E a convencao que todo mundo
          ja conhece, e evita um botao "voltar" a mais no cabecalho.
        */}
        <Link
          href="/"
          className="flex min-w-0 items-center gap-2 rounded-md transition-opacity hover:opacity-80"
        >
          {/*
            Logo e nome encolhem junto com a barra. Sao os dois unicos
            elementos que mudam de tamanho: os botoes a direita ficam como
            estao, porque alvo de toque que muda de tamanho e alvo que a
            pessoa erra.
          */}
          <Logo className="size-9 shrink-0 transition-[width,height] duration-300 ease-fg group-data-[scrolled=true]:size-7" />
          <Wordmark className="text-lg transition-[font-size] duration-300 ease-fg group-data-[scrolled=true]:text-base" />
        </Link>

        <div className="ml-auto flex items-center gap-1.5">
          {/*
            O selo so aparece na tela de analise.

            No institucional ele nao significa nada: aquela pagina e texto
            estatico e nao depende do backend para nada. Mostrar ali o estado
            de um servidor que a pessoa ainda nem vai usar e ruido - e, pior,
            um "API offline" vermelho na primeira tela passa a impressao de
            projeto quebrado quando nao ha nada quebrado.

            Na tela de analise ele aparece em TODOS os estados, inclusive
            "online". Ali o estado e acionavel: a area de upload depende dele,
            e com um servidor que hiberna e volta sozinho, ver que ficou
            pronto e justamente o que a pessoa esta esperando.
          */}
          {pathname === "/analyze" && (
            <ApiStatusBadge status={status} wakingSince={wakingSince} onRetry={retry} />
          )}

          {pathname !== "/analyze" && (
            <Button variant="outline" size="sm" asChild>
              <Link href="/analyze">{t("analyse")}</Link>
            </Button>
          )}

          <LanguageToggle />
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
