"use client";

import React, { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/Button";

export interface ResearchComposerProps {
  onSendMessage: (question: string) => void;
  onCancelGeneration?: () => void;
  isLoading: boolean;
  selectedSymbol: string;
}

const MAX_QUESTION_LENGTH = 1000;

export function ResearchComposer({
  onSendMessage,
  onCancelGeneration,
  isLoading,
  selectedSymbol,
}: ResearchComposerProps) {
  const [input, setInput] = useState<string>("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const sym = selectedSymbol || "SPY";

  const quickChips = [
    `What regime is ${sym} in?`,
    "How long has current regime lasted?",
    `Current volatility of ${sym}?`,
    "What does transition matrix show?",
    `Explain backtest for ${sym}`,
  ];

  // Auto-resize textarea height
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(
        textareaRef.current.scrollHeight,
        180
      )}px`;
    }
  }, [input]);

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const clean = input.trim();
    if (!clean || isLoading) return;

    onSendMessage(clean);
    setInput("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="research-composer-container" role="region" aria-label="Research Question Composer">
      {/* Quick Suggestion Chips */}
      <div className="research-composer-chips" aria-label="Quick inquiry suggestions">
        <span className="chips-label">Quick Prompts:</span>
        <div className="chips-scroll-row">
          {quickChips.map((chip) => (
            <button
              key={chip}
              type="button"
              className="quick-chip-btn"
              onClick={() => {
                setInput(chip);
                textareaRef.current?.focus();
              }}
              disabled={isLoading}
              aria-label={`Insert prompt: ${chip}`}
            >
              {chip}
            </button>
          ))}
        </div>
      </div>

      {/* Composer Form */}
      <form onSubmit={handleSubmit} className="research-composer-form">
        <div className="research-input-wrapper">
          <label htmlFor="research-question-input" className="sr-only">
            Ask a quantitative research question
          </label>
          <textarea
            id="research-question-input"
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value.slice(0, MAX_QUESTION_LENGTH))}
            onKeyDown={handleKeyDown}
            placeholder={`Ask about ${sym} regimes, risk, transition matrices, or historical backtests...`}
            rows={1}
            disabled={isLoading}
            className="research-textarea"
            aria-describedby="composer-char-count composer-instructions"
          />

          <div className="research-composer-actions">
            <span id="composer-char-count" className="char-count">
              {input.length}/{MAX_QUESTION_LENGTH}
            </span>

            {isLoading ? (
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={onCancelGeneration}
                className="research-cancel-btn"
                aria-label="Cancel generating research response"
              >
                ■ Stop
              </Button>
            ) : (
              <Button
                type="submit"
                variant="primary"
                size="sm"
                disabled={!input.trim()}
                className="research-submit-btn"
                aria-label="Submit research inquiry"
              >
                Inquire →
              </Button>
            )}
          </div>
        </div>
        <div id="composer-instructions" className="sr-only">
          Press Enter to submit inquiry, Shift+Enter for new line.
        </div>
      </form>
    </div>
  );
}
