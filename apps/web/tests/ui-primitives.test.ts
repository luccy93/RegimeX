import test from "node:test";
import assert from "node:assert";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import {
  Button,
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
  Badge,
  Input,
  Select,
  Alert,
  Spinner,
  Skeleton,
  EmptyState,
  ErrorState,
} from "../components/ui";

test("UI Primitives — Button", () => {
  // Default button
  const defaultHtml = renderToStaticMarkup(
    React.createElement(Button, null, "Click Me")
  );
  assert.ok(defaultHtml.includes("btn-primary"), "Default button has btn-primary");
  assert.ok(defaultHtml.includes("btn-md"), "Default button has btn-md");
  assert.ok(defaultHtml.includes("Click Me"), "Button renders label");

  // Danger variant, small size, disabled
  const dangerHtml = renderToStaticMarkup(
    React.createElement(Button, { variant: "danger", size: "sm", disabled: true }, "Delete")
  );
  assert.ok(dangerHtml.includes("btn-danger"), "Danger button has btn-danger");
  assert.ok(dangerHtml.includes("btn-sm"), "Small button has btn-sm");
  assert.ok(dangerHtml.includes("disabled"), "Disabled button has disabled attribute");

  // Loading state
  const loadingHtml = renderToStaticMarkup(
    React.createElement(Button, { isLoading: true }, "Submit")
  );
  assert.ok(loadingHtml.includes("btn-spinner"), "Loading button renders spinner");
  assert.ok(loadingHtml.includes("disabled"), "Loading button is disabled");
});

test("UI Primitives — Card and subcomponents", () => {
  const html = renderToStaticMarkup(
    React.createElement(
      Card,
      { variant: "elevated" },
      React.createElement(
        CardHeader,
        null,
        React.createElement(CardTitle, null, "Card Title"),
        React.createElement(CardDescription, null, "Card Desc")
      ),
      React.createElement(CardContent, null, "Card Content"),
      React.createElement(CardFooter, null, "Card Footer")
    )
  );

  assert.ok(html.includes("ui-card-elevated"), "Card has elevated class");
  assert.ok(html.includes("Card Title"), "Card renders title");
  assert.ok(html.includes("Card Desc"), "Card renders description");
  assert.ok(html.includes("Card Content"), "Card renders content");
  assert.ok(html.includes("Card Footer"), "Card renders footer");
});

test("UI Primitives — Badge", () => {
  const successBadge = renderToStaticMarkup(
    React.createElement(Badge, { variant: "success" }, "Active")
  );
  assert.ok(successBadge.includes("ui-badge-success"), "Badge has success class");
  assert.ok(successBadge.includes("Active"), "Badge renders text");

  const warningBadge = renderToStaticMarkup(
    React.createElement(Badge, { variant: "warning", size: "sm" }, "Pending")
  );
  assert.ok(warningBadge.includes("ui-badge-warning"), "Badge has warning class");
  assert.ok(warningBadge.includes("ui-badge-sm"), "Badge has small size class");
});

test("UI Primitives — Input accessibility and validation states", () => {
  // Input with error
  const errorHtml = renderToStaticMarkup(
    React.createElement(Input, {
      label: "Symbol",
      required: true,
      error: "Symbol is required",
      value: "",
      onChange: () => {},
    })
  );

  assert.ok(errorHtml.includes('aria-invalid="true"'), "Input with error has aria-invalid='true'");
  assert.ok(errorHtml.includes('role="alert"'), "Error message has role='alert'");
  assert.ok(errorHtml.includes("Symbol is required"), "Renders error text");
  assert.ok(errorHtml.includes('aria-hidden="true">*'), "Required indicator rendered");

  // Input with helper text
  const helperHtml = renderToStaticMarkup(
    React.createElement(Input, {
      label: "Lookup",
      helperText: "Enter canonical symbol (e.g. SPY)",
      value: "",
      onChange: () => {},
    })
  );
  assert.ok(helperHtml.includes("Enter canonical symbol"), "Renders helper text");
});

test("UI Primitives — Select component", () => {
  const options = [
    { value: "1d", label: "Daily" },
    { value: "1h", label: "Hourly" },
  ];
  const html = renderToStaticMarkup(
    React.createElement(Select, {
      label: "Interval",
      options,
      defaultValue: "1d",
    })
  );

  assert.ok(html.includes("<select"), "Renders select tag");
  assert.ok(html.includes('value="1d"'), "Renders first option value");
  assert.ok(html.includes("Daily"), "Renders first option label");
  assert.ok(html.includes('value="1h"'), "Renders second option value");
});

test("UI Primitives — Alert component", () => {
  const html = renderToStaticMarkup(
    React.createElement(
      Alert,
      { variant: "danger", title: "API Failure" },
      "Unable to reach server."
    )
  );

  assert.ok(html.includes('role="alert"'), "Alert has role='alert'");
  assert.ok(html.includes("ui-alert-danger"), "Alert has danger class");
  assert.ok(html.includes("API Failure"), "Alert renders title");
  assert.ok(html.includes("Unable to reach server."), "Alert renders body");
});

test("UI Primitives — Spinner and Skeleton", () => {
  const spinnerHtml = renderToStaticMarkup(
    React.createElement(Spinner, { size: "lg", label: "Fetching data..." })
  );
  assert.ok(spinnerHtml.includes('role="status"'), "Spinner has role='status'");
  assert.ok(spinnerHtml.includes("ui-spinner-lg"), "Spinner has lg size class");
  assert.ok(spinnerHtml.includes("Fetching data..."), "Spinner has accessible label");

  const skeletonHtml = renderToStaticMarkup(
    React.createElement(Skeleton, { shape: "circle", width: 40, height: 40 })
  );
  assert.ok(skeletonHtml.includes("ui-skeleton-circle"), "Skeleton has circle shape");
  assert.ok(skeletonHtml.includes('aria-hidden="true"'), "Skeleton is decorative/hidden");
});

test("UI Primitives — EmptyState and ErrorState", () => {
  const emptyHtml = renderToStaticMarkup(
    React.createElement(EmptyState, {
      title: "No Markets Found",
      description: "Adjust your filter criteria.",
      action: React.createElement(Button, null, "Reset Filters"),
    })
  );
  assert.ok(emptyHtml.includes("No Markets Found"), "EmptyState renders title");
  assert.ok(emptyHtml.includes("Adjust your filter criteria."), "EmptyState renders description");
  assert.ok(emptyHtml.includes("Reset Filters"), "EmptyState renders action");

  const errorHtml = renderToStaticMarkup(
    React.createElement(ErrorState, {
      title: "Load Failed",
      message: "Timeout while fetching data",
      requestId: "req_abc123",
      onRetry: () => {},
      retryLabel: "Retry Now",
    })
  );
  assert.ok(errorHtml.includes('role="alert"'), "ErrorState has role='alert'");
  assert.ok(errorHtml.includes("Load Failed"), "ErrorState renders title");
  assert.ok(errorHtml.includes("req_abc123"), "ErrorState renders request ID");
  assert.ok(errorHtml.includes("Retry Now"), "ErrorState renders retry button");
});
