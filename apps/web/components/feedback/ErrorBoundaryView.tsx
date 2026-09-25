"use client";

import React from "react";
import { Button } from "@/components/ui/Button";

export interface ErrorBoundaryViewProps {
  error: Error & { digest?: string };
  reset?: () => void;
  title?: string;
}

export function ErrorBoundaryView({
  error,
  reset,
  title = "Something went wrong",
}: ErrorBoundaryViewProps) {
  const correlationId = error.digest;

  return (
    <div className="error-boundary-container" role="alert" aria-live="assertive">
      <div className="error-boundary-card">
        <div className="error-boundary-icon" aria-hidden="true">
          ⚠️
        </div>
        <h2 className="error-boundary-title">{title}</h2>
        <p className="error-boundary-message">
          An unexpected error occurred while rendering this view. Our team has been notified.
        </p>

        {correlationId && (
          <div className="error-boundary-meta">
            <span className="error-boundary-label">Correlation ID:</span>
            <code className="error-boundary-code">{correlationId}</code>
          </div>
        )}

        <div className="error-boundary-actions">
          {reset && (
            <Button variant="primary" onClick={() => reset()}>
              Try Again
            </Button>
          )}
          <Button
            variant="outline"
            onClick={() => {
              if (typeof window !== "undefined") {
                window.location.href = "/";
              }
            }}
          >
            Return to Home
          </Button>
        </div>
      </div>
    </div>
  );
}
