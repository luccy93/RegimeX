import React from "react";
import { Spinner } from "@/components/ui/Spinner";

export default function ConsoleLoading() {
  return (
    <div
      className="page-loading-container"
      role="status"
      aria-live="polite"
      aria-label="Loading Console..."
    >
      <div className="page-loading-content">
        <Spinner size="md" label="Loading Console..." />
        <p className="page-loading-text">Loading Console...</p>
      </div>
    </div>
  );
}
