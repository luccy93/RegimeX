/**
 * RegimeX — Root Page (Foundation Proof-of-Concept)
 *
 * This page proves the Next.js App Router foundation is working.
 * It will be replaced by the Market Dashboard in a later volume.
 *
 * V04 scope: Foundation proof only.
 * Market Dashboard: Planned for V16+ (Platform Volume).
 */

import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "RegimeX — Market Intelligence Platform",
  description: "Open-source platform for market regime detection and quantitative research.",
};

export default function HomePage() {
  return (
    <main className="regimex-foundation-page">
      <div className="container">
        <header>
          <h1>RegimeX</h1>
          <p className="tagline">Open-Source Market Intelligence Platform</p>
        </header>

        <section className="status-section">
          <div className="status-badge">
            <span className="status-indicator" aria-label="Status: Engineering Foundation"></span>
            <span>V04 Engineering Foundation — In Progress</span>
          </div>
        </section>

        <section className="description-section">
          <p>
            RegimeX is an open-source platform that gives quantitative researchers,
            market analysts, and developers the infrastructure to understand market
            regimes — what they are, how they evolve, what risks they carry, and
            how strategies behave across them.
          </p>
          <p>
            The application foundation is being established. Market dashboards,
            regime analytics, and research workspaces will appear here in future
            platform volumes.
          </p>
        </section>

        <section className="volumes-section">
          <h2>Platform Development Status</h2>
          <ul className="volume-list">
            <li className="done">
              <strong>V01–V03</strong> — Product Foundation &amp; Architecture ✅
            </li>
            <li className="active">
              <strong>V04</strong> — Monorepo Engineering Foundation ⚙️
            </li>
            <li className="planned">
              <strong>V05–V12</strong> — Data &amp; Intelligence Pipeline 🔜
            </li>
            <li className="planned">
              <strong>V13–V15</strong> — Quantitative Analytics 🔜
            </li>
            <li className="planned">
              <strong>V16–V21</strong> — Platform &amp; AI Research 🔜
            </li>
            <li className="planned">
              <strong>V22–V30</strong> — Production &amp; 1.0 Release 🔜
            </li>
          </ul>
        </section>

        <footer>
          <p>
            <strong>Disclaimer:</strong> RegimeX is a research and analytics platform.
            It does not provide financial advice, personalized investment
            recommendations, or guarantees of returns. All platform outputs are for
            informational and research purposes only.
          </p>
          <p>
            <a
              href="https://github.com/luccy93/RegimeX"
              target="_blank"
              rel="noopener noreferrer"
            >
              View on GitHub
            </a>
          </p>
        </footer>
      </div>
    </main>
  );
}
