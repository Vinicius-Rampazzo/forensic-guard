/**
 * Area de upload com arrastar-e-soltar.
 *
 * Implementado com os eventos nativos do navegador, sem biblioteca. Sao quatro
 * eventos e uma armadilha:
 *
 *   dragEnter / dragOver  -> o arquivo esta sobre a area
 *   dragLeave             -> saiu
 *   drop                  -> soltou
 *
 * A armadilha: o comportamento PADRAO do navegador ao soltar um arquivo numa
 * pagina e abrir esse arquivo, substituindo a pagina inteira. Por isso todo
 * manipulador chama `preventDefault()` - inclusive o de dragOver, que a
 * primeira vista parece desnecessario. Sem ele, o evento `drop` nem dispara.
 */

"use client";

import { useRef, useState } from "react";

import { formatBytes } from "@/components/FileOverview";

const SUPPORTED_FORMATS = ["JPG", "PNG", "PDF", "EML", "DOCX", "ZIP", "EXE"];

interface FileDropzoneProps {
  onFileSelected: (file: File) => void;
  disabled?: boolean;
  /** Limite informado pelo backend. Null enquanto nao se sabe. */
  uploadLimit?: number | null;
}

export function FileDropzone({
  onFileSelected,
  disabled = false,
  uploadLimit = null,
}: FileDropzoneProps) {
  const [isDraggingOver, setIsDraggingOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  function handleDragOver(event: React.DragEvent) {
    event.preventDefault();

    if (!disabled) {
      setIsDraggingOver(true);
    }
  }

  function handleDragLeave(event: React.DragEvent) {
    event.preventDefault();
    setIsDraggingOver(false);
  }

  function handleDrop(event: React.DragEvent) {
    event.preventDefault();
    setIsDraggingOver(false);

    if (disabled) return;

    // Apenas o primeiro arquivo. A API analisa uma evidencia por vez, e
    // aceitar varios em silencio criaria a expectativa errada.
    const file = event.dataTransfer.files[0];

    if (file) {
      onFileSelected(file);
    }
  }

  function handleInputChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];

    if (file) {
      onFileSelected(file);
    }

    // Limpa o input para que escolher O MESMO arquivo de novo volte a
    // disparar o evento. Sem isso, reanalisar o mesmo arquivo nao funciona.
    event.target.value = "";
  }

  const borderStyle = isDraggingOver
    ? "border-emerald-500 bg-emerald-500/5"
    : "border-zinc-300 dark:border-zinc-700";

  return (
    <div
      onDragOver={handleDragOver}
      onDragEnter={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={`flex flex-col items-center gap-4 rounded-xl border-2 border-dashed px-6 py-16 text-center transition-colors ${borderStyle} ${
        disabled ? "opacity-50" : ""
      }`}
    >
      <div className="flex flex-col gap-1">
        <p className="text-base font-medium">Drop evidence here</p>
        <p className="text-sm text-zinc-500 dark:text-zinc-400">
          or select a file from your computer
        </p>
      </div>

      <button
        type="button"
        disabled={disabled}
        onClick={() => inputRef.current?.click()}
        className="rounded-md bg-zinc-900 px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:cursor-not-allowed dark:bg-zinc-100 dark:text-zinc-900"
      >
        Select file
      </button>

      {/*
        O input de arquivo e escondido e acionado pelo botao acima. Motivo:
        o input nativo nao pode ser estilizado de forma consistente entre
        navegadores, mas continua sendo ele quem abre o seletor do sistema.
      */}
      <input
        ref={inputRef}
        type="file"
        hidden
        onChange={handleInputChange}
        aria-label="Select evidence file"
      />

      <p className="font-mono text-xs text-zinc-400 dark:text-zinc-600">
        {SUPPORTED_FORMATS.join(" • ")} and more
      </p>

      {uploadLimit !== null && (
        <p className="text-xs text-zinc-400 dark:text-zinc-600">
          Up to {formatBytes(uploadLimit)} per file
        </p>
      )}
    </div>
  );
}
