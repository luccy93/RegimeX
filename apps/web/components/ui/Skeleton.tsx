import React from "react";
import { cn } from "@/lib/utils/cn";

export interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  shape?: "rect" | "circle" | "text";
  width?: string | number;
  height?: string | number;
}

export function Skeleton({
  className,
  shape = "rect",
  width,
  height,
  style,
  ...props
}: SkeletonProps) {
  const inlineStyles: React.CSSProperties = {
    ...style,
    width: width !== undefined ? width : undefined,
    height: height !== undefined ? height : undefined,
  };

  return (
    <div
      aria-hidden="true"
      className={cn(
        "ui-skeleton",
        shape === "circle" && "ui-skeleton-circle",
        shape === "text" && "ui-skeleton-text",
        className
      )}
      style={inlineStyles}
      {...props}
    />
  );
}
