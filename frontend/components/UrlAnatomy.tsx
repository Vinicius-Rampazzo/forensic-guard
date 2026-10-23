/**
 * A URL dissecada parte por parte, com cores.
 *
 * E o componente mais didatico do projeto. A tecnica de phishing mais comum
 * depende de o leitor nao perceber onde o dominio de verdade comeca - e
 * separar as partes em cores torna isso impossivel de confundir:
 *
 *     http://  www.banco.com.br@  203.0.113.45  :8443  /fatura.pdf.exe
 *     esquema  credenciais        HOST REAL     porta  caminho
 *              (ignorado)         (destacado)
 *
 * O destaque vai para o dominio registravel, porque e o unico pedaco que
 * determina para onde a URL realmente leva. Todo o resto pode ser escolhido
 * livremente por quem monta o endereco.
 */

"use client";

import { useTranslations } from "next-intl";

import { Card } from "@/components/Card";
import type { UrlParts } from "@/types/analysis";

interface SegmentProps {
  label: string;
  value: string;
  /** Destaque forte: esta e a parte que decide o destino. */
  primary?: boolean;
  /** Tom de alerta: esta parte e ignorada pelo navegador ou e suspeita. */
  alert?: boolean;
  muted?: boolean;
}

function Segment({ label, value, primary, alert, muted }: SegmentProps) {
  return (
    <span className="group/seg relative inline-flex flex-col">
      <span
        className={[
          "font-mono text-sm break-all",
          primary && "rounded px-1 font-semibold",
          alert && "rounded px-1 line-through decoration-2",
          muted && "text-muted-foreground",
        ]
          .filter(Boolean)
          .join(" ")}
        style={
          primary
            ? {
                background: "color-mix(in oklab, var(--brand-cyan) 18%, transparent)",
                color: "var(--brand-cyan)",
              }
            : alert
              ? {
                  background: "color-mix(in oklab, var(--brand-magenta) 15%, transparent)",
                  color: "var(--brand-magenta)",
                }
              : undefined
        }
      >
        {value}
      </span>
      <span className="mt-0.5 text-[9px] tracking-wider text-muted-foreground uppercase">
        {label}
      </span>
    </span>
  );
}

export function UrlAnatomy({ parts, url }: { parts: UrlParts; url: string }) {
  const t = useTranslations("url");

  const host = parts.unicode_host ?? parts.host;
  const subdomainText = parts.subdomains.length ? `${parts.subdomains.join(".")}.` : "";

  return (
    <Card title={t("anatomy")} hint={t("anatomyHint")}>
      <div className="flex flex-col gap-4">
        {/* A URL inteira, como foi enviada. */}
        <code className="block rounded bg-muted/40 px-3 py-2 font-mono text-xs break-all">
          {url}
        </code>

        {/* Agora separada, com a parte que importa em destaque. */}
        <div className="flex flex-wrap items-start gap-x-1 gap-y-3">
          <Segment label={t("scheme")} value={`${parts.scheme}://`} muted />

          {parts.username && (
            <Segment
              label={t("ignoredByBrowser")}
              value={`${parts.username}${parts.has_password ? ":•••" : ""}@`}
              alert
            />
          )}

          {subdomainText && <Segment label={t("subdomains")} value={subdomainText} muted />}

          <Segment label={t("realDestination")} value={parts.registrable_domain} primary />

          {parts.port !== null && (
            <Segment label={t("port")} value={`:${parts.port}`} muted />
          )}

          {parts.path && parts.path !== "/" && (
            <Segment label={t("path")} value={parts.path} muted />
          )}

          {parts.query && <Segment label={t("query")} value={`?${parts.query}`} muted />}

          {parts.fragment && (
            <Segment label={t("fragment")} value={`#${parts.fragment}`} muted />
          )}
        </div>

        {/*
          Quando o host esta em punycode, mostrar as duas formas e o ponto
          inteiro: o relatorio precisa exibir o que a VITIMA veria, nao o
          codigo que o navegador guarda.
        */}
        {parts.unicode_host && (
          <div className="flex flex-col gap-1 rounded border p-3">
            <p className="text-xs font-medium">{t("punycodeTitle")}</p>
            <div className="mt-1 flex flex-col gap-1 font-mono text-xs">
              <span>
                <span className="text-muted-foreground">{t("displaysAs")} </span>
                <span style={{ color: "var(--brand-magenta)" }}>{host}</span>
              </span>
              <span>
                <span className="text-muted-foreground">{t("actuallyIs")} </span>
                {parts.host}
              </span>
            </div>
          </div>
        )}

        {parts.is_private_host && (
          <p className="text-xs text-muted-foreground">{t("privateHost")}</p>
        )}
      </div>
    </Card>
  );
}
