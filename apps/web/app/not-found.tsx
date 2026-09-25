import React from "react";
import Link from "next/link";
import { Button } from "@/components/ui/Button";

export default function NotFound() {
  return (
    <div className="not-found-page" role="main" aria-labelledby="not-found-title">
      <div className="not-found-card">
        <span className="not-found-status">404</span>
        <h1 id="not-found-title" className="not-found-title">
          Page Not Found
        </h1>
        <p className="not-found-description">
          The requested page or resource could not be found. It may have been moved, renamed,
          or is not yet deployed on this platform.
        </p>

        <div className="not-found-actions">
          <Link href="/app">
            <Button variant="primary">Launch Console</Button>
          </Link>
          <Link href="/">
            <Button variant="outline">Return Home</Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
