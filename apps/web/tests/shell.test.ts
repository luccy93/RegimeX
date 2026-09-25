import test from "node:test";
import assert from "node:assert";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { AppShell } from "../components/layout/AppShell";
import { AppHeader } from "../components/layout/AppHeader";
import { AppSidebar } from "../components/layout/AppSidebar";

test("Application Shell — renders structural landmarks and accessibility features", () => {
  const html = renderToStaticMarkup(
    React.createElement(AppShell, null, React.createElement("div", { id: "test-content" }, "Inner"))
  );

  // Accessible landmarks
  assert.ok(html.includes('class="skip-to-content"'), "Shell must render skip-to-content link");
  assert.ok(html.includes('href="#main-content"'), "Skip link must target #main-content");
  assert.ok(html.includes('<header class="app-shell-header">'), "Shell must render header landmark");
  assert.ok(html.includes('<aside class="app-shell-sidebar"'), "Shell must render sidebar landmark");
  assert.ok(html.includes('id="main-content"'), "Shell must render main landmark with id");
  assert.ok(html.includes('id="test-content"'), "Shell must render children");
});

test("AppSidebar — renders primary navigation destinations and marks deferred routes", () => {
  const html = renderToStaticMarkup(React.createElement(AppSidebar, { currentPath: "/app" }));

  // Check required routes from Section 13
  assert.ok(html.includes('href="/app"'), "Sidebar must link to /app (Overview)");
  assert.ok(html.includes("Overview"), "Sidebar must label Overview");

  // Deferred routes should exist and be clearly marked as coming soon
  assert.ok(html.includes("Markets"), "Sidebar must have Markets entry");
  assert.ok(html.includes("Regimes"), "Sidebar must have Regimes entry");
  assert.ok(html.includes("Risk"), "Sidebar must have Risk entry");
  assert.ok(html.includes("Backtesting"), "Sidebar must have Backtesting entry");
  assert.ok(html.includes("Research"), "Sidebar must have Research entry");

  // Verify coming-soon badge / disabled indicator
  assert.ok(
    html.includes('aria-disabled="true"'),
    "Unimplemented routes must have aria-disabled='true'"
  );
  assert.ok(html.includes("V19"), "Markets/Regimes should show V19 indicator");
  assert.ok(html.includes("V20"), "Risk/Backtesting should show V20 indicator");
  assert.ok(html.includes("V21"), "Research should show V21 indicator");
});

test("AppHeader — renders platform status and branding", () => {
  const html = renderToStaticMarkup(React.createElement(AppHeader));

  assert.ok(html.includes("RegimeX"), "Header must include platform name");
  assert.ok(html.includes("Platform Core"), "Header must include platform status");
  assert.ok(html.includes('href="/app"'), "Header must link to /app");
  assert.ok(html.includes('href="/"'), "Header must link to home");
});
