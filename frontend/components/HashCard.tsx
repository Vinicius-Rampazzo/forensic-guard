/**
 * Hashes da evidencia, com botao de copiar.
 *
 * Copiar e a acao que o usuario mais faz nesta tela: o hash serve para
 * procurar a evidencia em bases publicas de indicadores. Obrigar a selecionar
 * 128 caracteres com o mouse seria hostil.
 */

"use client";

import { useState } from "react";

import { Card } from "@/components/Card";
import type { Hashes } from "@/types/analysis";

/** Ordem de exibicao, do mais usado em buscas ao mais forte. */
const ALGORITHMS: { key: keyof Hashes; label: string; note?: string }[] = [
  { key: "sha256", label: "SHA-256", note: "primary identifier" },
  { key: "md5", label: "MD5", note: "broken, but used by IOC lists" },
  { key: "sha1", label: "SHA-1", note: "broken, but still common" },
  { key: "sha512", label: "SHA-512" },
];

export function HashCard({ hashes }: { hashes: Hashes }) {
  return (
    <Card
      title="Hashes"
      hint="MD5 and SHA-1 are cryptographically broken. They are here to search with, never to trust."
    >
      <div className="flex flex-col gap-3">
        {ALGORITHMS.map(({ key, label, note }) => (
          <HashRow key={key} label={label} note={note} value={hashes[key]} />
        ))}
      </div>
    </Card>
  );
}

function HashRow({
  label,
  note,
  value,
}: {
  label: string;
  note?: string;
  value: string;
}) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      // Volta ao estado normal sozinho. Um "copied" permanente faria o
      // usuario duvidar se a copia seguinte funcionou.
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // A area de transferencia exige contexto seguro (HTTPS ou localhost) e
      // pode ser bloqueada pelo navegador. Falhar em silencio e melhor que
      // quebrar a pagina - o valor continua visivel para selecao manual.
    }
  }

  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center gap-2">
        <span className="text-xs font-medium">{label}</span>
        {note && <span className="text-[11px] text-zinc-400 dark:text-zinc-600">{note}</span>}
        <button
          type="button"
          onClick={copy}
          className="ml-auto rounded border border-zinc-200 px-2 py-0.5 text-[11px] text-zinc-500 transition-colors hover:border-zinc-400 dark:border-zinc-800 dark:text-zinc-400"
        >
          {copied ? "copied" : "copy"}
        </button>
      </div>
      <code className="rounded bg-zinc-50 px-2 py-1.5 font-mono text-[11px] break-all dark:bg-zinc-900/60">
        {value}
      </code>
    </div>
  );
}
