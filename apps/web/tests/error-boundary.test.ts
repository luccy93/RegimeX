import test from "node:test";
import assert from "node:assert";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { ErrorBoundaryView } from "../components/feedback/ErrorBoundaryView";

test("ErrorBoundaryView — renders user-safe error state with correlation ID", () => {
  const mockError = Object.assign(new Error("Sensitive internal database connection error"), {
    digest: "err_digest_987654",
  });

  const html = renderToStaticMarkup(
    React.createElement(ErrorBoundaryView, {
      error: mockError,
      reset: () => {},
    })
  );

  // Accessible semantics
  assert.ok(html.includes('role="alert"'), "Must have role='alert'");
  assert.ok(html.includes('aria-live="assertive"'), "Must have aria-live='assertive'");

  // User-safe title and description
  assert.ok(html.includes("Something went wrong"), "Must display user-safe heading");
  assert.ok(
    html.includes("An unexpected error occurred while rendering this view"),
    "Must display user-safe description"
  );

  // Must NOT leak raw internal stack/error message
  assert.ok(
    !html.includes("Sensitive internal database connection error"),
    "Must NOT leak sensitive raw error message to user"
  );

  // Preserves correlation digest for support
  assert.ok(html.includes("err_digest_987654"), "Must display correlation digest for support");

  // Recovery actions
  assert.ok(html.includes("Try Again"), "Must provide retry action button");
  assert.ok(html.includes("Return to Home"), "Must provide return home action button");
});
