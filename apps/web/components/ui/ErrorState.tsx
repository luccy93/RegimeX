import React from "react";
import { cn } from "@/lib/utils/cn";
import { Button } from "./Button";

export interface ErrorStateProps extends React.HTMLAttributes<HTMLDivElement> {
  title?: string;
  message?: string;
  requestId?: string;
  onRetry?: () => void;
  retryLabel?: string;
}

export function ErrorState({
  className,
  title = "An Error Occurred",
  message = "Unable to complete request. Please try again later.",
  requestId,
  onRetry,
  retryLabel = "Try Again",
  ...props
}: ErrorStateProps) {
  return (
    <div role="alert" className={cn("ui-error-state", className)} {...props}>
      <div className="ui-error-state-icon" aria-hidden="true">
        ⚠️
      </div>
      <h4 className="ui-error-state-title">{title}</h4>
      <p className="ui-error-state-message">{message}</p>
      {requestId && (
        <p className="ui-error-state-request-id">
          <span>Request ID:</span> <code>{requestId}</code>
        </p>
      )}
      {onRetry && (
        <div className="ui-error-state-action">
          <Button variant="secondary" size="sm" onClick={onRetry}>
            {retryLabel}
          </Button>
        </div>
      )}
    </div>
  );
}
