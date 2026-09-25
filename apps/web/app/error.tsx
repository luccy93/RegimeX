"use client";

import React, { useEffect } from "react";
import { ErrorBoundaryView } from "@/components/feedback/ErrorBoundaryView";

export default function RootError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // In production, log to telemetry service with correlation ID
    // Avoid logging sensitive credentials
  }, [error]);

  return <ErrorBoundaryView error={error} reset={reset} />;
}
