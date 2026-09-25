import React from "react";
import Link from "next/link";
import { Badge } from "@/components/ui/Badge";
import { getAppVersion } from "@/lib/config/env";

export function AppHeader() {
  const version = getAppVersion();

  return (
    <header className="app-shell-header">
      <div className="header-container">
        <div className="header-left">
          <Link href="/app" className="brand-logo" aria-label="RegimeX App Console">
            <span className="brand-mark">RX</span>
            <span className="brand-title">RegimeX</span>
          </Link>
          <Badge variant="outline" size="sm" className="brand-badge">
            v{version}
          </Badge>
          <div className="header-status">
            <span className="status-dot" aria-hidden="true" />
            <span className="status-label">Platform Core</span>
          </div>
        </div>

        <nav className="header-right" aria-label="Header Navigation">
          <Link href="/" className="header-link">
            Home
          </Link>
          <Link href="/app" className="header-link header-link-active">
            Console
          </Link>
          <a
            href="https://github.com/luccy93/RegimeX"
            target="_blank"
            rel="noopener noreferrer"
            className="header-link"
          >
            GitHub
          </a>
        </nav>
      </div>
    </header>
  );
}
