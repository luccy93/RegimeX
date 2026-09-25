import test from "node:test";
import assert from "node:assert";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import NotFound from "../app/not-found";

test("NotFound Page — renders accessible 404 with navigation options", () => {
  const html = renderToStaticMarkup(React.createElement(NotFound));

  assert.ok(html.includes('role="main"'), "Must have role='main' landmark");
  assert.ok(html.includes("404"), "Must display 404 status indicator");
  assert.ok(html.includes("Page Not Found"), "Must display Page Not Found title");
  assert.ok(
    html.includes("The requested page or resource could not be found"),
    "Must explain page was not found"
  );
  assert.ok(html.includes('href="/app"'), "Must provide link to console");
  assert.ok(html.includes('href="/"'), "Must provide link to home");
});
