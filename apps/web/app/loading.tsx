import React from "react";
import { Spinner } from "@/components/ui/Spinner";

export default function RootLoading() {
  return (
    <div
      className="page-loading-container"
      role="status"
      aria-live="polite"
      aria-label="Loading RegimeX platform..."
    >
      <div className="page-loading-content">
        <Spinner size="lg" label="Loading RegimeX platform..." />
        <p className="page-loading-text">Loading RegimeX...</p>
      </div>
    </div>
  );
}
