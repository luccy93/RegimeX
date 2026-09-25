/**
 * RegimeX Web — Separator Component
 * Volume 18 — Commit 02
 *
 * Accessible horizontal or vertical visual divider.
 * Follows WAI-ARIA separator role pattern.
 */
import React from "react";
import { cn } from "@/lib/utils/cn";

export interface SeparatorProps extends React.HTMLAttributes<HTMLHRElement> {
  orientation?: "horizontal" | "vertical";
  decorative?: boolean;
}

export function Separator({
  className,
  orientation = "horizontal",
  decorative = true,
  ...props
}: SeparatorProps) {
  return (
    <hr
      role={decorative ? "none" : "separator"}
      aria-orientation={decorative ? undefined : orientation}
      className={cn(
        "ui-separator",
        orientation === "horizontal" && "ui-separator-horizontal",
        orientation === "vertical" && "ui-separator-vertical",
        className
      )}
      {...props}
    />
  );
}
