"use client";

import React from "react";
import type { CitationDTO } from "@/lib/api/types";

export interface ResearchCitationChipProps {
  id: number;
  citation?: CitationDTO;
  onClick: (id: number) => void;
  isSelected?: boolean;
}

export function ResearchCitationChip({
  id,
  citation,
  onClick,
  isSelected = false,
}: ResearchCitationChipProps) {
  const tooltipText = citation
    ? `${citation.title}${citation.symbol ? ` — ${citation.symbol}` : ""}`
    : `Source [${id}]`;

  return (
    <button
      type="button"
      className={`research-citation-chip ${isSelected ? "selected" : ""}`}
      onClick={() => onClick(id)}
      title={tooltipText}
      aria-label={`View evidence source [${id}]: ${tooltipText}`}
      aria-pressed={isSelected}
    >
      <span className="research-citation-bracket">[</span>
      <span className="research-citation-num">{id}</span>
      <span className="research-citation-bracket">]</span>
    </button>
  );
}
