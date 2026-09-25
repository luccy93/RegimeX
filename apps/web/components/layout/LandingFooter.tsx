import React from "react";
import Link from "next/link";

export function LandingFooter() {
  return (
    <footer className="landing-footer">
      <div className="landing-container">
        <div className="landing-footer-grid">
          <div className="landing-footer-brand-col">
            <div className="brand-logo">
              <span className="brand-mark">RX</span>
              <span className="brand-title">RegimeX</span>
            </div>
            <p className="landing-footer-tagline">
              Open-Source Market Intelligence and Quantitative Research Platform.
            </p>
          </div>

          <div className="landing-footer-col">
            <h5 className="landing-footer-col-title">Navigation</h5>
            <ul className="landing-footer-list">
              <li>
                <Link href="/">Home</Link>
              </li>
              <li>
                <Link href="/app">Console</Link>
              </li>
              <li>
                <a href="#capabilities">Capabilities</a>
              </li>
              <li>
                <a href="#architecture">Architecture</a>
              </li>
            </ul>
          </div>

          <div className="landing-footer-col">
            <h5 className="landing-footer-col-title">Resources</h5>
            <ul className="landing-footer-list">
              <li>
                <a
                  href="https://github.com/luccy93/RegimeX"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  GitHub Repository
                </a>
              </li>
              <li>
                <a
                  href="https://github.com/luccy93/RegimeX/blob/main/README.md"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Documentation
                </a>
              </li>
              <li>
                <a
                  href="https://github.com/luccy93/RegimeX/blob/main/LICENSE"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  License
                </a>
              </li>
            </ul>
          </div>
        </div>

        <div className="landing-footer-disclaimer">
          <p>
            <strong>Disclaimer:</strong> RegimeX is an open-source technical research and analytics
            platform. It does not provide financial advice, trading signals, or investment
            recommendations. All outputs are intended strictly for quantitative research, engineering,
            and informational purposes.
          </p>
          <p className="landing-footer-copy">
            &copy; {new Date().getFullYear()} RegimeX Contributors. Open-source under MIT / Apache-2.0.
          </p>
        </div>
      </div>
    </footer>
  );
}
