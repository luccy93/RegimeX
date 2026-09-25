import React from "react";
import Link from "next/link";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { getAppVersion } from "@/lib/config/env";

export function LandingHeader() {
  const version = getAppVersion();

  return (
    <header className="landing-header">
      <div className="landing-container landing-header-inner">
        <div className="landing-brand">
          <Link href="/" className="brand-logo" aria-label="RegimeX Homepage">
            <span className="brand-mark">RX</span>
            <span className="brand-title">RegimeX</span>
          </Link>
          <Badge variant="outline" size="sm" className="brand-badge">
            v{version}
          </Badge>
        </div>

        <nav className="landing-nav" aria-label="Main Navigation">
          <a href="#capabilities" className="landing-nav-link">
            Capabilities
          </a>
          <a href="#architecture" className="landing-nav-link">
            Architecture
          </a>
          <a href="#principles" className="landing-nav-link">
            Principles
          </a>
          <a
            href="https://github.com/luccy93/RegimeX"
            target="_blank"
            rel="noopener noreferrer"
            className="landing-nav-link"
          >
            GitHub
          </a>
          <Link href="/app">
            <Button variant="primary" size="sm">
              Console
            </Button>
          </Link>
        </nav>
      </div>
    </header>
  );
}
