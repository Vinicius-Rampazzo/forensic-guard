/**
 * Navegacao por abas do relatorio.
 *
 * Implementado com os atributos ARIA de tablist. Nao e enfeite: sem eles, um
 * leitor de tela anuncia apenas uma fileira de botoes, sem dizer que formam um
 * conjunto nem qual esta ativo.
 */

"use client";

import type { ReactNode } from "react";

export interface Tab {
  id: string;
  label: string;
  content: ReactNode;
}

interface TabsProps {
  tabs: Tab[];
  activeId: string;
  onSelect: (id: string) => void;
}

export function Tabs({ tabs, activeId, onSelect }: TabsProps) {
  const active = tabs.find((tab) => tab.id === activeId) ?? tabs[0];

  return (
    <div className="flex flex-col gap-4">
      {/* overflow-x-auto para que muitas abas rolem no celular em vez de
          espremerem umas as outras ate ficarem ilegiveis. */}
      <div
        role="tablist"
        aria-label="Report sections"
        className="flex gap-1 overflow-x-auto border-b border-zinc-200 dark:border-zinc-800"
      >
        {tabs.map((tab) => {
          const isActive = tab.id === active.id;

          return (
            <button
              key={tab.id}
              role="tab"
              id={`tab-${tab.id}`}
              aria-selected={isActive}
              aria-controls={`panel-${tab.id}`}
              onClick={() => onSelect(tab.id)}
              className={`shrink-0 border-b-2 px-3 py-2 text-sm transition-colors ${
                isActive
                  ? "border-emerald-500 font-medium"
                  : "border-transparent text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100"
              }`}
            >
              {tab.label}
            </button>
          );
        })}
      </div>

      <div role="tabpanel" id={`panel-${active.id}`} aria-labelledby={`tab-${active.id}`}>
        {active.content}
      </div>
    </div>
  );
}
