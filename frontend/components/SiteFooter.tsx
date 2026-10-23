/**
 * Rodape, compartilhado pelas duas rotas.
 *
 * Carrega as duas frases que precisam estar visiveis em qualquer tela: que
 * nada sai da maquina, e que a ferramenta nao emite veredito. A segunda e
 * exigencia do proprio projeto - um relatorio forense nao pode dar a entender
 * que afirma mais do que afirma.
 */

"use client";

import { useTranslations } from "next-intl";

export function SiteFooter() {
  const t = useTranslations("app");

  return (
    <footer className="border-t">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-1 px-6 py-5 text-[11px] text-muted-foreground">
        <p className="font-medium">{t("privacyLine")}</p>
        <p>{t("disclaimerLine")}</p>
      </div>
    </footer>
  );
}
