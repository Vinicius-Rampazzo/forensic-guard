/**
 * Area de upload com arrastar-e-soltar.
 *
 * Implementado com os eventos nativos do navegador, sem biblioteca. Sao tres
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

import { UploadCloud } from "lucide-react";
import { useTranslations } from "next-intl";
import { useRef, useState } from "react";

import { formatBytes } from "@/components/format";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

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
  const t = useTranslations("upload");
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

  return (
    <div
      onDragOver={handleDragOver}
      onDragEnter={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={cn(
        "flex flex-col items-center gap-5 rounded-xl border-2 border-dashed px-6 py-14 text-center transition-all duration-200",
        isDraggingOver
          ? "scale-[1.01] border-[var(--brand-cyan)] bg-[color-mix(in_oklab,var(--brand-cyan)_7%,transparent)]"
          : "border-border hover:border-foreground/25",
        disabled && "pointer-events-none opacity-50",
      )}
    >
      <div
        className={cn(
          "flex size-12 items-center justify-center rounded-full border transition-all duration-200",
          isDraggingOver
            ? "scale-110 border-[var(--brand-cyan)]/40 bg-[color-mix(in_oklab,var(--brand-cyan)_12%,transparent)]"
            : "border-border bg-muted/40",
        )}
      >
        <UploadCloud
          className={cn(
            "size-5 transition-colors duration-200",
            isDraggingOver ? "text-[var(--brand-cyan)]" : "text-muted-foreground",
          )}
        />
      </div>

      <div className="flex flex-col gap-1">
        <p className="text-base font-medium">
          {isDraggingOver ? t("release") : t("drop")}
        </p>
        <p className="text-sm text-muted-foreground">
          {t("or")}
        </p>
      </div>

      <Button type="button" disabled={disabled} onClick={() => inputRef.current?.click()}>
        {t("select")}
      </Button>

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

      <div className="flex flex-col items-center gap-1">
        <p className="font-mono text-xs text-muted-foreground">
          {SUPPORTED_FORMATS.join(" · ")} {t("andMore")}
        </p>
        {uploadLimit !== null && (
          <p className="text-xs text-muted-foreground">
            {t("limit", { size: formatBytes(uploadLimit) })}
          </p>
        )}
      </div>
    </div>
  );
}
