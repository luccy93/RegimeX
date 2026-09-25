import React from "react";
import { cn } from "@/lib/utils/cn";

export interface SpinnerProps extends React.HTMLAttributes<HTMLDivElement> {
  size?: "sm" | "md" | "lg";
  label?: string;
}

export function Spinner({
  className,
  size = "md",
  label = "Loading...",
  ...props
}: SpinnerProps) {
  return (
    <div
      role="status"
      aria-label={label}
      className={cn(
        "ui-spinner",
        size === "sm" && "ui-spinner-sm",
        size === "md" && "ui-spinner-md",
        size === "lg" && "ui-spinner-lg",
        className
      )}
      {...props}
    >
      <span className="sr-only">{label}</span>
    </div>
  );
}
