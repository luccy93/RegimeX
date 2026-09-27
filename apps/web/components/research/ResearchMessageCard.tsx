"use client";

import React, { useState } from "react";
import type { CitationDTO, ResearchMessage } from "@/lib/api/types";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";
import { Alert } from "@/components/ui/Alert";
import { ResearchCitationChip } from "./ResearchCitationChip";

export interface ResearchMessageCardProps {
  message: ResearchMessage;
  onSelectCitation: (id: number) => void;
  onOpenEvidencePanel: () => void;
  onRetry?: (question: string) => void;
  selectedCitationId?: number | null;
}

export function ResearchMessageCard({
  message,
  onSelectCitation,
  onOpenEvidencePanel,
  onRetry,
  selectedCitationId,
}: ResearchMessageCardProps) {
  const isUser = message.role === "user";
  const [sourcesExpanded, setSourcesExpanded] = useState<boolean>(true);

  if (isUser) {
    return (
      <div className="research-msg-row user-row">
        <div className="research-user-bubble">
          <div className="research-user-header">
            <span className="research-user-avatar" aria-hidden="true">👤</span>
            <span className="research-user-label">Research Query</span>
            <span className="research-msg-time">
              {new Date(message.timestamp).toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
              })}
            </span>
          </div>
          <div className="research-user-text">{message.content}</div>
        </div>
      </div>
    );
  }

  // Assistant message rendering
  const citations = message.citations || [];
  const citationsMap = new Map<number, CitationDTO>(
    citations.map((c) => [c.id, c])
  );

  /**
   * Parse text and replace citation markers like [1], [2] with interactive components.
   */
  const renderFormattedContent = (content: string) => {
    if (!content) return null;

    // Split paragraphs
    const paragraphs = content.split(/\n\n+/);

    return paragraphs.map((para, pIdx) => {
      // Split tokens by citation tags [N]
      const parts = para.split(/(\[\d+\])/g);

      return (
        <p key={pIdx} className="research-answer-paragraph">
          {parts.map((part, idx) => {
            const match = part.match(/^\[(\d+)\]$/);
            if (match) {
              const citId = parseInt(match[1], 10);
              const cit = citationsMap.get(citId);
              return (
                <ResearchCitationChip
                  key={idx}
                  id={citId}
                  citation={cit}
                  onClick={(id) => {
                    onSelectCitation(id);
                    onOpenEvidencePanel();
                  }}
                  isSelected={selectedCitationId === citId}
                />
              );
            }

            // Simple markdown bold formatting **text**
            const boldParts = part.split(/(\*\*[^*]+\*\*)/g);
            return (
              <span key={idx}>
                {boldParts.map((bPart, bIdx) => {
                  if (bPart.startsWith("**") && bPart.endsWith("**")) {
                    return <strong key={bIdx}>{bPart.slice(2, -2)}</strong>;
                  }
                  return <span key={bIdx}>{bPart}</span>;
                })}
              </span>
            );
          })}
        </p>
      );
    });
  };

  return (
    <div
      className={`research-msg-row assistant-row status-${message.status || "complete"}`}
      aria-live={message.status === "streaming" ? "polite" : undefined}
    >
      <div className="research-assistant-card">
        {/* Assistant Header */}
        <div className="research-assistant-header">
          <div className="assistant-header-left">
            <span className="research-logo-icon" aria-hidden="true">⚡</span>
            <span className="assistant-name">RegimeX Assistant</span>
            {message.model && (
              <Badge variant="outline" size="sm" className="assistant-model-badge">
                {message.model}
              </Badge>
            )}
            {message.intent && (
              <Badge variant="default" size="sm" className="assistant-intent-badge">
                {message.intent}
              </Badge>
            )}
          </div>
          <span className="research-msg-time">
            {new Date(message.timestamp).toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </span>
        </div>

        {/* Loading State */}
        {message.status === "loading" && (
          <div className="research-loading-state" aria-busy="true">
            <Spinner size="sm" />
            <span className="research-loading-text">
              Retrieving verified platform intelligence and assembling grounded answer...
            </span>
          </div>
        )}

        {/* Error State */}
        {message.status === "error" && (
          <div className="research-error-state">
            <Alert variant="danger">
              <div className="research-error-content">
                <p>{message.error || "An error occurred while evaluating the research query."}</p>
                {onRetry && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => onRetry(message.content)}
                    className="research-retry-btn"
                  >
                    Retry Query
                  </Button>
                )}
              </div>
            </Alert>
          </div>
        )}

        {/* Answer Content */}
        {message.content && (
          <div className="research-answer-body">
            {renderFormattedContent(message.content)}
            {message.status === "streaming" && (
              <span className="research-streaming-cursor" aria-hidden="true">▊</span>
            )}
          </div>
        )}

        {/* Citations & Evidence Footer */}
        {citations.length > 0 && message.status !== "loading" && (
          <div className="research-citations-footer">
            <div className="research-citations-header">
              <button
                type="button"
                className="research-sources-toggle"
                onClick={() => setSourcesExpanded(!sourcesExpanded)}
                aria-expanded={sourcesExpanded}
              >
                <span className="toggle-icon">{sourcesExpanded ? "▾" : "▸"}</span>
                <span className="toggle-title">
                  Grounded Citations ({citations.length} verified source{citations.length === 1 ? "" : "s"})
                </span>
              </button>

              <Button
                variant="ghost"
                size="sm"
                onClick={onOpenEvidencePanel}
                className="open-evidence-drawer-btn"
                aria-label="Open full evidence audit drawer"
              >
                Inspect Audit Evidence →
              </Button>
            </div>

            {sourcesExpanded && (
              <ul className="research-citations-list">
                {citations.map((c) => (
                  <li key={c.id} className="research-citation-item">
                    <button
                      type="button"
                      className={`research-citation-link ${selectedCitationId === c.id ? "active" : ""}`}
                      onClick={() => {
                        onSelectCitation(c.id);
                        onOpenEvidencePanel();
                      }}
                      aria-label={`Inspect source [${c.id}]: ${c.title}`}
                    >
                      <span className="citation-badge">[{c.id}]</span>
                      <span className="citation-title">{c.title}</span>
                      {c.facts_summary && (
                        <span className="citation-facts-preview">— {c.facts_summary}</span>
                      )}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}

        <div className="research-disclaimer-note">
          Quantitative analytics interface • Not individualized financial advice • Non-predictive
        </div>
      </div>
    </div>
  );
}
