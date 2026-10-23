/**
 * Links e URLs encontrados na mensagem.
 *
 * O destaque e para os links ENGANOSOS: aqueles cujo texto exibe um endereco
 * e cujo destino aponta para outro. Por isso a tela mostra os dois lados lado
 * a lado - ver so um deles nunca revela a discrepancia.
 *
 * Nenhuma URL e clicavel. Numa ferramenta forense, transformar o endereco
 * suspeito em link seria entregar ao usuario a arma apontada para ele.
 */

import { Card } from "@/components/Card";
import type { EmailLink } from "@/types/analysis";

interface UrlListProps {
  links: EmailLink[];
  urls: string[];
}

export function UrlList({ links, urls }: UrlListProps) {
  const misleading = links.filter((link) => link.misleading);
  const honest = links.filter((link) => !link.misleading);

  // URLs que aparecem no corpo mas nao sao links do HTML - texto puro, por
  // exemplo. Elas nao tem texto exibido para comparar.
  const linkUrls = new Set(links.map((link) => link.url));
  const looseUrls = urls.filter((url) => !linkUrls.has(url));

  return (
    <div className="flex flex-col gap-4">
      {misleading.length > 0 && (
        <Card
          title="Misleading links"
          hint="The displayed address does not match the destination. This is the defining technique of phishing."
        >
          <ul className="flex flex-col gap-3">
            {misleading.map((link, index) => (
              <li
                key={`${index}-${link.url}`}
                className="rounded border border-red-500/30 bg-red-500/5 p-3"
              >
                <div className="flex flex-col gap-1">
                  <Side label="reader sees" value={link.display_text} />
                  <Side label="actually goes to" value={link.url} emphasis />
                </div>
              </li>
            ))}
          </ul>
        </Card>
      )}

      <Card title="Links" hint="URLs are shown as text and are never clickable.">
        {honest.length === 0 && looseUrls.length === 0 ? (
          <p className="text-sm text-muted-foreground">No other links found.</p>
        ) : (
          <ul className="flex flex-col gap-2">
            {honest.map((link, index) => (
              <li key={`${index}-${link.url}`} className="flex flex-col gap-0.5">
                {link.display_text && (
                  <span className="text-xs text-muted-foreground">
                    {link.display_text}
                  </span>
                )}
                <code className="rounded bg-muted/40 px-2 py-1 font-mono text-[11px] break-all ">
                  {link.url}
                </code>
              </li>
            ))}

            {looseUrls.map((url, index) => (
              <li key={`${index}-${url}`}>
                <code className="block rounded bg-muted/40 px-2 py-1 font-mono text-[11px] break-all ">
                  {url}
                </code>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}

function Side({
  label,
  value,
  emphasis = false,
}: {
  label: string;
  value: string;
  emphasis?: boolean;
}) {
  return (
    <div className="flex flex-col gap-0.5 sm:flex-row sm:gap-3">
      <span className="shrink-0 text-[11px] text-muted-foreground sm:w-32">
        {label}
      </span>
      <code
        className={`min-w-0 font-mono text-[11px] break-all ${
          emphasis ? "text-red-600 dark:text-red-400" : ""
        }`}
      >
        {value || "—"}
      </code>
    </div>
  );
}
