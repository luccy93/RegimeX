/**
 * RegimeX Web — Tooltip Component
 * Volume 18 — Commit 02
 *
 * CSS-only accessible tooltip using the title-like pattern.
 * No JavaScript positioning library required — uses CSS custom positioning.
 * Hover and focus reveal.
 */
import React from "react";
import { cn } from "@/lib/utils/cn";

export interface TooltipProps {
  /** The tooltip content text */
  content: string;
  /** The trigger element */
  children: React.ReactNode;
  /** Placement hint (visual only — CSS-driven) */
  placement?: "top" | "bottom" | "left" | "right";
  /** Custom class for the tooltip wrapper */
  className?: string;
}

/**
 * Tooltip — wraps a trigger element and shows a floating label on hover/focus.
 *
 * Usage:
 *   <Tooltip content="Regime probability score">
 *     <span>0.87</span>
 *   </Tooltip>
 */
export function Tooltip({
  content,
  children,
  placement = "top",
  className,
}: TooltipProps) {
  return (
    <span
      className={cn("ui-tooltip-wrapper", className)}
      data-tooltip={content}
      data-placement={placement}
    >
      {children}
      <span
        role="tooltip"
        className={cn(
          "ui-tooltip-bubble",
          placement === "top" && "ui-tooltip-top",
          placement === "bottom" && "ui-tooltip-bottom",
          placement === "left" && "ui-tooltip-left",
          placement === "right" && "ui-tooltip-right"
        )}
        aria-hidden="true"
      >
        {content}
      </span>
    </span>
  );
}
