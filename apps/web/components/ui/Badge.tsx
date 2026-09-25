import React from "react";
import { cn } from "@/lib/utils/cn";

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "default" | "success" | "warning" | "danger" | "info" | "outline";
  size?: "sm" | "md";
}

export function Badge({
  className,
  variant = "default",
  size = "md",
  children,
  ...props
}: BadgeProps) {
  return (
    <span
      className={cn(
        "ui-badge",
        variant === "default" && "ui-badge-default",
        variant === "success" && "ui-badge-success",
        variant === "warning" && "ui-badge-warning",
        variant === "danger" && "ui-badge-danger",
        variant === "info" && "ui-badge-info",
        variant === "outline" && "ui-badge-outline",
        size === "sm" && "ui-badge-sm",
        size === "md" && "ui-badge-md",
        className
      )}
      {...props}
    >
      {children}
    </span>
  );
}
