/**
 * Cabecalhos da mensagem e resultado da autenticacao.
 *
 * A tela precisa comunicar, sem exigir que o usuario saiba de forense, que
 * **quase todo cabecalho e escrito por quem envia**. From, Subject e Date nao
 * sao verificados por nada. Os campos com peso probatorio sao a cadeia de
 * Received e o resultado da autenticacao, acrescentados pelos servidores.
 */

import { Card, DataList, DataRow, Empty } from "@/components/Card";
import type { Authentication, EmailAnalysis } from "@/types/analysis";

export function EmailHeaders({ email }: { email: EmailAnalysis }) {
  if (email.error) {
    return (
      <Card title="Email">
        <p className="text-sm text-amber-600 dark:text-amber-400">{email.error}</p>
      </Card>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <Card
        title="Headers"
        hint="Almost every header below is written by the sender and verified by nothing."
      >
        <DataList>
          {Object.entries(email.headers).map(([name, value]) => (
            <DataRow key={name} label={name}>
              {value || <Empty />}
            </DataRow>
          ))}
        </DataList>
      </Card>

      <Card title="Sender consistency">
        <DataList>
          <DataRow label="From domain" mono>
            {email.from_domain ?? <Empty />}
          </DataRow>

          <DataRow label="Reply-To domain" mono>
            {email.reply_to_domain ?? <Empty />}
            {email.reply_to_mismatch && <MismatchNote>replies go elsewhere</MismatchNote>}
          </DataRow>

          <DataRow label="Return-Path domain" mono>
            {email.return_path_domain ?? <Empty />}
            {email.return_path_mismatch && (
              <MismatchNote>bounces go elsewhere</MismatchNote>
            )}
          </DataRow>
        </DataList>
      </Card>

      <AuthenticationCard authentication={email.authentication} />

      <Card
        title="Received chain"
        hint="Added by the servers the message passed through, newest first. One of the few parts the sender cannot write."
      >
        {email.received_chain.length === 0 ? (
          <p className="text-sm text-zinc-500 dark:text-zinc-400">
            No Received headers. The message may never have been delivered.
          </p>
        ) : (
          <ol className="flex flex-col gap-2">
            {email.received_chain.map((hop, index) => (
              <li
                key={`${index}-${hop.slice(0, 40)}`}
                className="rounded bg-zinc-50 px-2 py-1.5 font-mono text-[11px] break-all dark:bg-zinc-900/60"
              >
                {hop}
              </li>
            ))}
          </ol>
        )}
      </Card>
    </div>
  );
}

function MismatchNote({ children }: { children: string }) {
  return (
    <span className="ml-2 font-sans text-xs text-amber-600 dark:text-amber-400">
      differs from sender — {children}
    </span>
  );
}

/** Resultados que indicam falha de verificacao, espelhando o backend. */
const FAILURE_RESULTS = new Set(["fail", "softfail", "permerror", "temperror", "policy"]);

function AuthenticationCard({ authentication }: { authentication: Authentication }) {
  const methods: { label: string; value: string | null; note: string }[] = [
    {
      label: "SPF",
      value: authentication.spf,
      note: "was the sending server allowed to send for this domain",
    },
    {
      label: "DKIM",
      value: authentication.dkim,
      note: "did the signature over the message verify",
    },
    {
      label: "DMARC",
      value: authentication.dmarc,
      note: "did the message satisfy the domain owner's policy",
    },
  ];

  return (
    <Card
      title="Authentication"
      hint="Read from the Authentication-Results header. ForensicGuard does not re-check over DNS."
    >
      <DataList>
        {methods.map(({ label, value, note }) => (
          <DataRow key={label} label={label}>
            {value === null ? (
              <Empty>not reported</Empty>
            ) : (
              <span
                className={
                  FAILURE_RESULTS.has(value.toLowerCase())
                    ? "font-medium text-red-600 dark:text-red-400"
                    : "font-medium text-emerald-600 dark:text-emerald-400"
                }
              >
                {value}
              </span>
            )}
            <span className="ml-2 text-xs text-zinc-400 dark:text-zinc-600">{note}</span>
          </DataRow>
        ))}
      </DataList>

      {authentication.raw === null && (
        <p className="mt-3 border-t border-zinc-100 pt-3 text-xs text-zinc-500 dark:border-zinc-900 dark:text-zinc-400">
          No authentication results in this message. Not having a result is
          different from having failed — a file exported before delivery never
          passed through a verifying server.
        </p>
      )}
    </Card>
  );
}
