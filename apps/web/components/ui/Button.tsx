import React from "react";
import { cn } from "@/lib/utils/cn";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "outline" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
  isLoading?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant = "primary",
      size = "md",
      isLoading = false,
      disabled,
      children,
      type = "button",
      ...props
    },
    ref
  ) => {
    return (
      <button
        ref={ref}
        type={type}
        disabled={disabled || isLoading}
        className={cn(
          "inline-flex items-center justify-center font-medium transition-colors select-none",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2",
          // Styles based on variant
          variant === "primary" && "btn-primary",
          variant === "secondary" && "btn-secondary",
          variant === "outline" && "btn-outline",
          variant === "ghost" && "btn-ghost",
          variant === "danger" && "btn-danger",
          // Size
          size === "sm" && "btn-sm",
          size === "md" && "btn-md",
          size === "lg" && "btn-lg",
          (disabled || isLoading) && "btn-disabled",
          className
        )}
        {...props}
      >
        {isLoading && (
          <span
            className="btn-spinner"
            aria-hidden="true"
            style={{
              display: "inline-block",
              width: "1em",
              height: "1em",
              marginRight: "0.5rem",
              border: "2px solid currentColor",
              borderTopColor: "transparent",
              borderRadius: "50%",
              animation: "spin 0.6s linear infinite",
            }}
          />
        )}
        <span>{children}</span>
      </button>
    );
  }
);

Button.displayName = "Button";
