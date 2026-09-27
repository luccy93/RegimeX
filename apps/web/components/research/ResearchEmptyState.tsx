"use client";

import React from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";

export interface ResearchEmptyStateProps {
  onSelectPrompt: (question: string) => void;
  selectedSymbol: string;
}

interface StarterCategory {
  title: string;
  badge: string;
  icon: string;
  questions: string[];
}

export function ResearchEmptyState({
  onSelectPrompt,
  selectedSymbol,
}: ResearchEmptyStateProps) {
  const sym = selectedSymbol || "SPY";

  const categories: StarterCategory[] = [
    {
      title: "Regime Intelligence",
      badge: "Classification",
      icon: "📊",
      questions: [
        `What regime is ${sym} currently in?`,
        "How long has the current regime lasted?",
        "What are the historical characteristics of this regime?",
      ],
    },
    {
      title: "Markov Transitions",
      badge: "Dynamics",
      icon: "🔄",
      questions: [
        `What does the transition matrix show for ${sym}?`,
        `How frequently has ${sym} transitioned between regimes?`,
        "What is the regime persistence probability?",
      ],
    },
    {
      title: "Portfolio Risk",
      badge: "VaR & Drawdown",
      icon: "📉",
      questions: [
        `What is the current volatility of ${sym}?`,
        "What was the maximum drawdown during this period?",
        "What is the 95% Value at Risk (VaR) and Expected Shortfall?",
      ],
    },
    {
      title: "Backtesting & Assumptions",
      badge: "Execution",
      icon: "⚡",
      questions: [
        `Explain the latest backtest results for ${sym}.`,
        "What assumptions were used in this backtest?",
        "Compare the current regime with historical regime profiles.",
      ],
    },
  ];

  return (
    <div className="research-empty-state" role="region" aria-label="Research Assistant Overview">
      <div className="research-empty-hero">
        <div className="research-hero-icon" aria-hidden="true">🧠</div>
        <h2 className="research-hero-title">Quantitative Research Assistant</h2>
        <p className="research-hero-text">
          Ask questions about market regimes, empirical transition matrices, portfolio risk analytics,
          and historical backtests. Every factual answer is strictly derived from RegimeX platform data with explicit citations.
        </p>

        <div className="research-hero-disclaimer">
          <span className="disclaimer-badge">Institutional Scope:</span>
          <span>
            RegimeX provides quantitative research and historical model analytics.
            It does not provide future price predictions, trading signals, or personalized investment advice.
          </span>
        </div>
      </div>

      <div className="research-starters-section">
        <h3 className="research-starters-heading">Suggested Research Inquiries:</h3>
        <div className="research-starters-grid">
          {categories.map((cat) => (
            <Card key={cat.title} variant="bordered" className="research-starter-category-card">
              <CardHeader className="starter-card-header">
                <div className="starter-header-row">
                  <span className="starter-cat-icon" aria-hidden="true">{cat.icon}</span>
                  <CardTitle className="starter-cat-title">{cat.title}</CardTitle>
                </div>
                <Badge variant="outline" size="sm">
                  {cat.badge}
                </Badge>
              </CardHeader>
              <CardContent className="starter-card-content">
                <ul className="starter-question-list">
                  {cat.questions.map((q) => (
                    <li key={q}>
                      <button
                        type="button"
                        className="starter-question-btn"
                        onClick={() => onSelectPrompt(q)}
                        aria-label={`Ask: ${q}`}
                      >
                        <span className="starter-arrow">→</span>
                        <span className="starter-text">{q}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}
