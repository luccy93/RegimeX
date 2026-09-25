import test from "node:test";
import assert from "node:assert";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import LandingPage from "../app/page";

test("Root Page — renders RegimeX branding and core messaging", () => {
  const html = renderToStaticMarkup(React.createElement(LandingPage));

  // Branding & title
  assert.ok(html.includes("RegimeX"), "Page should render RegimeX title/branding");
  assert.ok(
    html.includes("Open-Source Market Intelligence Platform"),
    "Page should render platform subtitle/tagline"
  );

  // Accessible landmarks
  assert.ok(html.includes('id="main-content"'), "Page must have #main-content landmark");
  assert.ok(html.includes('class="skip-to-content"'), "Page must have accessible skip link");
  assert.ok(html.includes("<header"), "Page must render a semantic header");
  assert.ok(html.includes("<main"), "Page must render a semantic main");
  assert.ok(html.includes("<footer"), "Page must render a semantic footer");

  // Primary navigation & CTAs
  assert.ok(html.includes('href="/app"'), "Page must link to /app Console");
  assert.ok(
    html.includes("https://github.com/luccy93/RegimeX"),
    "Page must link to official GitHub repository"
  );

  // Core capabilities sections
  assert.ok(html.includes("Market Regime Detection"), "Page must explain regime detection");
  assert.ok(html.includes("Empirical Transition Analytics"), "Page must explain transition analytics");
  assert.ok(html.includes("Portfolio Risk Intelligence"), "Page must explain risk intelligence");
  assert.ok(html.includes("Systematic Backtesting"), "Page must explain systematic backtesting");
});
