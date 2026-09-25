import React from "react";
import type { Metadata } from "next";
import Link from "next/link";
import { LandingHeader } from "@/components/layout/LandingHeader";
import { LandingFooter } from "@/components/layout/LandingFooter";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";

export const metadata: Metadata = {
  title: "RegimeX — Open-Source Market Intelligence Platform",
  description:
    "Systematic market regime detection, transition analytics, and quantitative research infrastructure.",
};

export default function LandingPage() {
  const capabilities = [
    {
      title: "Market Regime Detection",
      badge: "V08 Core",
      description:
        "Multi-algorithm ensemble detection (Gaussian Mixture Models, Hidden Markov Models, and KMeans) with canonicalized labels across volatility and trend states.",
    },
    {
      title: "Empirical Transition Analytics",
      badge: "V09 Core",
      description:
        "Markovian transition matrices, persistence probabilities, spell durations, and Shannon entropy metrics quantifying regime shift dynamics.",
    },
    {
      title: "Portfolio Risk Intelligence",
      badge: "V10 Core",
      description:
        "Cross-regime Value at Risk (VaR), Conditional VaR, maximum drawdown, and downside volatility profiles aligned to market states.",
    },
    {
      title: "Systematic Backtesting",
      badge: "V11 Core",
      description:
        "Event-driven strategy simulation accounting for execution slippage, regime filtering, and point-in-time benchmark performance.",
    },
  ];

  const architecturalPrinciples = [
    {
      title: "Pure Domain Logic",
      description:
        "Domain models remain pure Python and independent of databases, web frameworks, or vendor APIs.",
    },
    {
      title: "Reproducible Quantitative Research",
      description:
        "Deterministic algorithms, versioned models, and immutable configuration contracts prevent lookahead and data leakage.",
    },
    {
      title: "Typed REST Transport",
      description:
        "FastAPI backend with Pydantic v2 schemas and strict TypeScript API client bindings.",
    },
    {
      title: "Zero Black-Box Dependencies",
      description:
        "All statistical formulas, scalers, and ensemble voters are open, audited, and mathematically verified.",
    },
  ];

  return (
    <div className="landing-page">
      <a href="#main-content" className="skip-to-content">
        Skip to main content
      </a>
      <LandingHeader />

      <main id="main-content" className="landing-main">
        {/* 1. Hero Section */}
        <section className="landing-hero" aria-labelledby="hero-heading">
          <div className="landing-container">
            <div className="hero-content">
              <div className="hero-badge-wrapper">
                <Badge variant="info" size="sm">
                  Volume 18 — Web Platform Foundation
                </Badge>
              </div>
              <h1 id="hero-heading" className="hero-title">
                Open-Source Market Intelligence Platform
              </h1>
              <p className="hero-lead">
                RegimeX provides quantitative researchers, portfolio analysts, and engineers with
                transparent infrastructure to detect market regimes, quantify transition dynamics,
                and analyze cross-regime risk.
              </p>
              <div className="hero-actions">
                <Link href="/app">
                  <Button variant="primary" size="lg">
                    Launch Platform Console
                  </Button>
                </Link>
                <a
                  href="https://github.com/luccy93/RegimeX"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <Button variant="outline" size="lg">
                    View on GitHub
                  </Button>
                </a>
              </div>
            </div>
          </div>
        </section>

        {/* 2. What RegimeX Does */}
        <section className="landing-section" aria-labelledby="about-heading">
          <div className="landing-container">
            <div className="section-header">
              <h2 id="about-heading" className="section-title">
                What RegimeX Does
              </h2>
              <p className="section-subtitle">
                Financial markets do not follow a single stationary distribution. RegimeX treats
                market states as discrete, identifiable regimes with distinct risk and return profiles.
              </p>
            </div>

            <div className="about-grid">
              <div className="about-card">
                <div className="about-icon" aria-hidden="true">
                  🔍
                </div>
                <h3 className="about-title">Identify Unobservable States</h3>
                <p className="about-text">
                  Classify historical and real-time market data into canonical regimes using statistical
                  clustering and unsupervised machine learning models.
                </p>
              </div>
              <div className="about-card">
                <div className="about-icon" aria-hidden="true">
                  🔄
                </div>
                <h3 className="about-title">Measure Transition Probabilities</h3>
                <p className="about-text">
                  Analyze how regimes transition over time, identifying persistence spells, change
                  probabilities, and systemic instability.
                </p>
              </div>
              <div className="about-card">
                <div className="about-icon" aria-hidden="true">
                  🛡️
                </div>
                <h3 className="about-title">Condition Risk and Strategies</h3>
                <p className="about-text">
                  Evaluate value-at-risk, drawdown potential, and strategy performance conditioned on
                  the prevailing market regime rather than aggregate assumptions.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* 3. Core Capabilities */}
        <section id="capabilities" className="landing-section landing-section-alt" aria-labelledby="capabilities-heading">
          <div className="landing-container">
            <div className="section-header">
              <h2 id="capabilities-heading" className="section-title">
                Core Capabilities
              </h2>
              <p className="section-subtitle">
                Built upon the proven statistical engines and domain services established in Volumes 01–17.
              </p>
            </div>

            <div className="capabilities-grid">
              {capabilities.map((cap) => (
                <Card key={cap.title} variant="elevated">
                  <CardHeader>
                    <div className="card-badge-row">
                      <Badge variant="outline" size="sm">
                        {cap.badge}
                      </Badge>
                    </div>
                    <CardTitle>{cap.title}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <CardDescription>{cap.description}</CardDescription>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        </section>

        {/* 4. Architecture & Principles */}
        <section id="architecture" className="landing-section" aria-labelledby="architecture-heading">
          <div className="landing-container">
            <div className="section-header">
              <h2 id="architecture-heading" className="section-title">
                Architecture &amp; Transparency
              </h2>
              <p className="section-subtitle">
                Designed for institutional rigor, testability, and algorithmic transparency.
              </p>
            </div>

            <div className="principles-grid">
              {architecturalPrinciples.map((principle) => (
                <div key={principle.title} className="principle-item">
                  <h4 className="principle-title">{principle.title}</h4>
                  <p className="principle-text">{principle.description}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* 5. Call to Action */}
        <section className="landing-cta" aria-labelledby="cta-heading">
          <div className="landing-container">
            <div className="cta-box">
              <h2 id="cta-heading" className="cta-title">
                Explore the Web Platform Foundation
              </h2>
              <p className="cta-description">
                Explore the responsive application shell and route architecture. Interactive dashboards
                and analytics visualizers are scheduled for deployment in Volumes 19 and 20.
              </p>
              <div className="cta-actions">
                <Link href="/app">
                  <Button variant="primary" size="lg">
                    Open Platform Shell
                  </Button>
                </Link>
              </div>
            </div>
          </div>
        </section>
      </main>

      <LandingFooter />
    </div>
  );
}
