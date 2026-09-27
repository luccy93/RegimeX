"use client";

import React from "react";
import type { CitationDTO, EvidencePacketDTO } from "@/lib/api/types";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

export interface ResearchEvidencePanelProps {
  isOpen: boolean;
  onClose: () => void;
  citations: CitationDTO[];
  evidence: EvidencePacketDTO[];
  selectedCitationId: number | null;
  onSelectCitation: (id: number) => void;
}

export function ResearchEvidencePanel({
  isOpen,
  onClose,
  citations,
  evidence,
  selectedCitationId,
  onSelectCitation,
}: ResearchEvidencePanelProps) {
  if (!isOpen) return null;

  return (
    <aside
      className="research-evidence-panel"
      role="complementary"
      aria-label="Verified Grounded Evidence and Citations"
    >
      <div className="research-evidence-header">
        <div className="research-evidence-header-title">
          <span className="research-evidence-icon" aria-hidden="true">🔬</span>
          <h3>Audit Evidence & Provenance</h3>
        </div>
        <div className="research-evidence-header-actions">
          <Badge variant="default" size="sm">
            {evidence.length} Packet{evidence.length === 1 ? "" : "s"}
          </Badge>
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            aria-label="Close evidence panel"
            className="research-evidence-close-btn"
          >
            ✕
          </Button>
        </div>
      </div>

      <div className="research-evidence-content">
        {evidence.length === 0 && citations.length === 0 ? (
          <div className="research-evidence-empty">
            <p>No factual evidence packets available for this message.</p>
          </div>
        ) : (
          <div className="research-evidence-list">
            {citations.map((citation) => {
              const isSelected = selectedCitationId === citation.id;
              const matchingPacket = evidence.find(
                (p) => p.source_id === citation.source_id
              );

              return (
                <div
                  key={citation.id}
                  id={`evidence-citation-${citation.id}`}
                  className={`research-evidence-card ${isSelected ? "highlighted" : ""}`}
                  tabIndex={0}
                >
                  <div className="research-evidence-card-header">
                    <span className="research-evidence-badge-num">[{citation.id}]</span>
                    <h4 className="research-evidence-card-title">{citation.title}</h4>
                  </div>

                  <div className="research-evidence-meta-row">
                    <Badge variant="outline" size="sm">
                      {citation.source_type}
                    </Badge>
                    {citation.symbol && (
                      <span className="research-evidence-symbol">
                        Symbol: <strong>{citation.symbol}</strong>
                      </span>
                    )}
                    {citation.timestamp && (
                      <span className="research-evidence-time">
                        {new Date(citation.timestamp).toLocaleDateString(undefined, {
                          month: "short",
                          day: "numeric",
                          year: "numeric",
                        })}
                      </span>
                    )}
                  </div>

                  {citation.model && (
                    <div className="research-evidence-model">
                      <span className="meta-key">Engine / Provenance:</span>{" "}
                      <span className="meta-val">{citation.model}</span>
                    </div>
                  )}

                  {matchingPacket && Object.keys(matchingPacket.facts).length > 0 && (
                    <div className="research-evidence-facts-section">
                      <h5 className="research-facts-heading">Verified Platform Facts:</h5>
                      <div className="research-facts-grid">
                        {Object.entries(matchingPacket.facts).map(([key, value]) => {
                          let displayVal = String(value);
                          if (typeof value === "number") {
                            displayVal = Number.isInteger(value)
                              ? String(value)
                              : value.toFixed(4);
                          } else if (typeof value === "object" && value !== null) {
                            displayVal = JSON.stringify(value);
                          }

                          return (
                            <div key={key} className="research-fact-row">
                              <span className="fact-key">{key.replace(/_/g, " ")}:</span>
                              <span className="fact-val">{displayVal}</span>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  <div className="research-evidence-source-id">
                    <code>source_id: {citation.source_id}</code>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </aside>
  );
}
