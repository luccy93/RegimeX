"use client";

import React from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";

export function RiskMethodologySection() {
  return (
    <section className="risk-methodology-section" aria-labelledby="risk-methodology-title">
      <div className="section-header">
        <div>
          <h2 id="risk-methodology-title" className="section-title">Analytical Methodology & Risk Disclosures</h2>
          <p className="section-subtitle">
            Mathematical foundations, loss orientation semantics, and statistical limitations governing V13 risk calculations.
          </p>
        </div>
        <Badge variant="outline" size="sm">Reproducible Analytics</Badge>
      </div>

      <div className="risk-methodology-grid">
        <Card variant="bordered" className="methodology-card">
          <CardHeader>
            <CardTitle className="methodology-card-title">1. Return Definition & Scaling</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="methodology-text">
              Daily returns are computed as discrete percentage relative changes:{" "}
              <code className="methodology-code">R_t = (P_t - P_(t-1)) / P_(t-1)</code>.
              Annualized volatility scales period volatility by the square root of annual observations:{" "}
              <code className="methodology-code">σ_ann = σ_period × √(252)</code>.
            </p>
          </CardContent>
        </Card>

        <Card variant="bordered" className="methodology-card">
          <CardHeader>
            <CardTitle className="methodology-card-title">2. Loss-Oriented VaR & Expected Shortfall</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="methodology-text">
              Value at Risk is reported under the strict loss-positive convention:{" "}
              <code className="methodology-code">VaR_α = -Quantile_(1-α)(R)</code>.
              Expected Shortfall (Conditional VaR) is the coherent risk measure calculating the arithmetic mean of all tail losses exceeding the VaR cutoff:{" "}
              <code className="methodology-code">ES_α = -E[R | R ≤ -VaR_α]</code>.
            </p>
          </CardContent>
        </Card>

        <Card variant="bordered" className="methodology-card">
          <CardHeader>
            <CardTitle className="methodology-card-title">3. Downside Deviation & Semi-Variance</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="methodology-text">
              Downside deviation evaluates the root-mean-square of negative excess returns relative to a target benchmark{" "}
              <code className="methodology-code">T = 0.00%</code>:{" "}
              <code className="methodology-code">DD = √( (1/N) ∑ min(0, R_t - T)² )</code>.
              Semi-variance represents the un-rooted downside dispersion squared.
            </p>
          </CardContent>
        </Card>

        <Card variant="bordered" className="methodology-card">
          <CardHeader>
            <CardTitle className="methodology-card-title">4. Model Limitations & Non-Stationarity</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="methodology-text">
              Calculations assume historical empirical distributions and do not model live execution slippage or future structural breaks.
              Financial asset returns exhibit fat tails, volatility clustering, and regime transitions that may render standard Gaussian assumptions conservative or invalid in stress scenarios.
            </p>
          </CardContent>
        </Card>
      </div>
    </section>
  );
}
