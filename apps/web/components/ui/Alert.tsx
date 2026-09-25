import React from "react";
import { cn } from "@/lib/utils/cn";

export interface AlertProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "info" | "success" | "warning" | "danger";
  title?: string;
}

export function Alert({
  className,
  variant = "info",
  title,
  children,
  ...props
}: AlertProps) {
  return (
    <div
      role="alert"
      className={cn(
        "ui-alert",
        variant === "info" && "ui-alert-info",
        variant === "success" && "ui-alert-success",
        variant === "warning" && "ui-alert-warning",
        variant === "danger" && "ui-alert-danger",
        className
      )}
      {...props}
    >
      {title && <h5 className="ui-alert-title">{title}</h5>}
      <div className="ui-alert-body">{children}</div>
    </div>
  );
}
