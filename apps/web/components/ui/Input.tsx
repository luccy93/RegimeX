import React from "react";
import { cn } from "@/lib/utils/cn";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, error, helperText, id, required, ...props }, ref) => {
    const inputId = id || (label ? label.toLowerCase().replace(/\s+/g, "-") : undefined);
    const errorId = inputId ? `${inputId}-error` : undefined;
    const helperId = inputId ? `${inputId}-helper` : undefined;

    return (
      <div className="ui-input-wrapper">
        {label && (
          <label htmlFor={inputId} className="ui-input-label">
            {label}
            {required && <span className="ui-input-required" aria-hidden="true">*</span>}
          </label>
        )}
        <input
          ref={ref}
          id={inputId}
          required={required}
          aria-invalid={error ? "true" : undefined}
          aria-describedby={
            error ? errorId : helperText ? helperId : undefined
          }
          className={cn("ui-input", error && "ui-input-error", className)}
          {...props}
        />
        {error && (
          <p id={errorId} className="ui-input-error-text" role="alert">
            {error}
          </p>
        )}
        {!error && helperText && (
          <p id={helperId} className="ui-input-helper-text">
            {helperText}
          </p>
        )}
      </div>
    );
  }
);

Input.displayName = "Input";
