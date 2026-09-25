/**
 * RegimeX Web — Design System Token Tests
 * Volume 18 — Commit 02
 *
 * Validates:
 *   - Token exports exist and are the correct types
 *   - Token values are valid CSS colors / values
 *   - Chart palette has 8 entries in correct order
 *   - Aggregated `tokens` map includes all sub-objects
 *   - RegimeColors cover all required regime states
 *   - Z-Index hierarchy is monotonically increasing
 *   - Motion tokens are non-empty strings
 *   - Layout constants are non-empty strings
 */
import test from "node:test";
import assert from "node:assert/strict";

import {
  surface,
  border,
  foreground,
  brand,
  semanticColors,
  regimeColors,
  chartPalette,
  typography,
  spacing,
  radius,
  shadows,
  motion,
  zIndex,
  layout,
  tokens,
} from "@/lib/design-system/tokens";

// ─────────────────────────────────────────────────────────────────────────────
// 1. Surface Tokens
// ─────────────────────────────────────────────────────────────────────────────
test("design-system/tokens — surface tokens are defined", () => {
  assert.equal(typeof surface.background, "string");
  assert.ok(surface.background.length > 0, "background must be non-empty");
  assert.equal(typeof surface.surface, "string");
  assert.equal(typeof surface.surfaceMuted, "string");
  assert.equal(typeof surface.surfaceElevated, "string");
  assert.equal(typeof surface.surfaceGlass, "string");
  assert.ok(surface.surfaceGlass.includes("rgba"), "glass surface must use rgba");
});

// ─────────────────────────────────────────────────────────────────────────────
// 2. Border Tokens
// ─────────────────────────────────────────────────────────────────────────────
test("design-system/tokens — border tokens are defined", () => {
  assert.equal(typeof border.border, "string");
  assert.equal(typeof border.borderFocus, "string");
  assert.equal(typeof border.borderGlass, "string");
  assert.ok(border.borderGlass.includes("rgba"), "borderGlass must use rgba");
});

// ─────────────────────────────────────────────────────────────────────────────
// 3. Brand Tokens
// ─────────────────────────────────────────────────────────────────────────────
test("design-system/tokens — brand tokens are defined", () => {
  assert.equal(typeof brand.primary, "string");
  assert.ok(brand.primary.startsWith("#"), "primary must be a hex color");
  assert.equal(typeof brand.primaryHover, "string");
  assert.equal(typeof brand.focus, "string");
  assert.equal(typeof brand.primarySubtle, "string");
  assert.ok(brand.primarySubtle.includes("rgba"), "primarySubtle must use rgba");
});

// ─────────────────────────────────────────────────────────────────────────────
// 4. Semantic Color Tokens
// ─────────────────────────────────────────────────────────────────────────────
test("design-system/tokens — semantic colors all have 4 variants (base/subtle/fg/border)", () => {
  const states = ["success", "warning", "danger", "info"] as const;
  for (const state of states) {
    const base = state;
    const subtle = `${state}Subtle` as keyof typeof semanticColors;
    const fg = `${state}Foreground` as keyof typeof semanticColors;
    const borderKey = `${state}Border` as keyof typeof semanticColors;

    assert.ok(semanticColors[base as keyof typeof semanticColors], `${state} must exist`);
    assert.ok(semanticColors[subtle], `${subtle} must exist`);
    assert.ok(semanticColors[fg], `${fg} must exist`);
    assert.ok(semanticColors[borderKey], `${borderKey} must exist`);
    assert.ok(
      (semanticColors[subtle] as string).includes("rgba"),
      `${subtle} must be rgba`
    );
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// 5. Regime Color Tokens
// ─────────────────────────────────────────────────────────────────────────────
test("design-system/tokens — regimeColors covers all 6 regime states", () => {
  const requiredStates = [
    "bullish",
    "bearish",
    "transitioning",
    "neutral",
    "highVolatility",
    "lowVolatility",
  ] as const;

  for (const state of requiredStates) {
    assert.ok(
      regimeColors[state as keyof typeof regimeColors],
      `regimeColors.${state} must be defined`
    );
  }
});

test("design-system/tokens — regime colors have base, subtle and foreground", () => {
  // Spot check bullish
  assert.ok(regimeColors.bullish.startsWith("#"), "bullish must be hex");
  assert.ok(regimeColors.bullishSubtle.includes("rgba"), "bullishSubtle must be rgba");
  assert.ok(regimeColors.bullishForeground.startsWith("#"), "bullishForeground must be hex");

  // Spot check bearish
  assert.ok(regimeColors.bearish.startsWith("#"), "bearish must be hex");
  assert.ok(regimeColors.bearishSubtle.includes("rgba"), "bearishSubtle must be rgba");
});

// ─────────────────────────────────────────────────────────────────────────────
// 6. Chart Palette
// ─────────────────────────────────────────────────────────────────────────────
test("design-system/tokens — chartPalette has exactly 8 entries", () => {
  assert.equal(chartPalette.length, 8);
});

test("design-system/tokens — all chartPalette entries are valid hex colors", () => {
  const hexPattern = /^#[0-9a-fA-F]{3,8}$/;
  for (let i = 0; i < chartPalette.length; i++) {
    assert.match(
      chartPalette[i],
      hexPattern,
      `chartPalette[${i}] must be a valid hex color`
    );
  }
});

test("design-system/tokens — chartPalette first entry is blue (primary series)", () => {
  assert.equal(chartPalette[0], "#3b82f6");
});

test("design-system/tokens — chartPalette second entry is emerald (secondary series)", () => {
  assert.equal(chartPalette[1], "#10b981");
});

// ─────────────────────────────────────────────────────────────────────────────
// 7. Z-Index Hierarchy
// ─────────────────────────────────────────────────────────────────────────────
test("design-system/tokens — z-index hierarchy is monotonically increasing", () => {
  const levels = [
    zIndex.base,
    zIndex.raised,
    zIndex.dropdown,
    zIndex.sticky,
    zIndex.header,
    zIndex.modal,
    zIndex.tooltip,
    zIndex.toast,
  ];

  for (let i = 1; i < levels.length; i++) {
    assert.ok(
      levels[i] > levels[i - 1],
      `z-index[${i}]=${levels[i]} must be > z-index[${i - 1}]=${levels[i - 1]}`
    );
  }
});

test("design-system/tokens — tooltip z-index is above modal", () => {
  assert.ok(zIndex.tooltip > zIndex.modal, "tooltip must be above modal");
});

test("design-system/tokens — toast z-index is the highest", () => {
  const allValues = Object.values(zIndex);
  const maxValue = Math.max(...allValues);
  assert.equal(zIndex.toast, maxValue, "toast must have the highest z-index");
});

// ─────────────────────────────────────────────────────────────────────────────
// 8. Motion Tokens
// ─────────────────────────────────────────────────────────────────────────────
test("design-system/tokens — motion duration tokens are ms strings", () => {
  const durations = [
    motion.durationInstant,
    motion.durationFast,
    motion.durationBase,
    motion.durationSlow,
    motion.durationVerySlow,
  ];

  for (const d of durations) {
    assert.ok(d.endsWith("ms"), `duration "${d}" must end with ms`);
    const ms = parseFloat(d);
    assert.ok(ms > 0, `duration "${d}" must be positive`);
  }
});

test("design-system/tokens — motion duration values are ordered fast to slow", () => {
  const instant = parseFloat(motion.durationInstant);
  const fast = parseFloat(motion.durationFast);
  const base = parseFloat(motion.durationBase);
  const slow = parseFloat(motion.durationSlow);
  const verySlow = parseFloat(motion.durationVerySlow);

  assert.ok(instant < fast, "instant must be shorter than fast");
  assert.ok(fast < base, "fast must be shorter than base");
  assert.ok(base < slow, "base must be shorter than slow");
  assert.ok(slow < verySlow, "slow must be shorter than verySlow");
});

test("design-system/tokens — motion easing strings are non-empty", () => {
  const easings = [
    motion.easingDefault,
    motion.easingLinear,
    motion.easingIn,
    motion.easingOut,
    motion.easingInOut,
    motion.easingSpring,
  ];

  for (const e of easings) {
    assert.ok(e.length > 0, `easing "${e}" must be non-empty`);
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// 9. Typography Tokens
// ─────────────────────────────────────────────────────────────────────────────
test("design-system/tokens — font sizes are rem strings", () => {
  const sizes = [
    typography.fontSizeXs,
    typography.fontSizeSm,
    typography.fontSizeBase,
    typography.fontSizeLg,
    typography.fontSizeXl,
    typography.fontSize2xl,
    typography.fontSize3xl,
    typography.fontSize4xl,
  ];

  for (const s of sizes) {
    assert.ok(s.endsWith("rem"), `font size "${s}" must be in rem`);
    const val = parseFloat(s);
    assert.ok(val > 0, `font size "${s}" must be positive`);
  }
});

test("design-system/tokens — font sizes are ordered small to large", () => {
  const toRem = (s: string) => parseFloat(s);
  const sizes = [
    typography.fontSizeXs,
    typography.fontSizeSm,
    typography.fontSizeBase,
    typography.fontSizeLg,
    typography.fontSizeXl,
    typography.fontSize2xl,
    typography.fontSize3xl,
    typography.fontSize4xl,
  ].map(toRem);

  for (let i = 1; i < sizes.length; i++) {
    assert.ok(
      sizes[i] > sizes[i - 1],
      `font size[${i}]=${sizes[i]} must be > font size[${i - 1}]=${sizes[i - 1]}`
    );
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// 10. Layout Constants
// ─────────────────────────────────────────────────────────────────────────────
test("design-system/tokens — layout constants are non-empty strings", () => {
  const layoutValues = Object.values(layout);
  assert.ok(layoutValues.length >= 4, "layout must have at least 4 constants");
  for (const v of layoutValues) {
    assert.equal(typeof v, "string");
    assert.ok(v.length > 0, "layout constant must be non-empty");
  }
});

test("design-system/tokens — chart height values parse correctly", () => {
  const minH = parseFloat(layout.chartMinHeight);
  const stdH = parseFloat(layout.chartDefaultHeight);
  const tallH = parseFloat(layout.chartTallHeight);

  assert.ok(minH > 0, "chartMinHeight must be positive");
  assert.ok(stdH > minH, "chartDefaultHeight must be > chartMinHeight");
  assert.ok(tallH > stdH, "chartTallHeight must be > chartDefaultHeight");
});

// ─────────────────────────────────────────────────────────────────────────────
// 11. Spacing Tokens
// ─────────────────────────────────────────────────────────────────────────────
test("design-system/tokens — spacing values are rem strings", () => {
  const spacingValues = Object.values(spacing);
  for (const v of spacingValues) {
    assert.ok(v.endsWith("rem"), `spacing "${v}" must be in rem`);
    const val = parseFloat(v);
    assert.ok(val > 0, `spacing "${v}" must be positive`);
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// 12. Aggregated Token Map
// ─────────────────────────────────────────────────────────────────────────────
test("design-system/tokens — aggregated tokens map includes all sections", () => {
  const requiredSections = [
    "surface",
    "border",
    "foreground",
    "brand",
    "semanticColors",
    "regimeColors",
    "chartPalette",
    "typography",
    "spacing",
    "radius",
    "shadows",
    "motion",
    "zIndex",
    "layout",
  ] as const;

  for (const section of requiredSections) {
    assert.ok(
      tokens[section as keyof typeof tokens] !== undefined,
      `tokens.${section} must be defined in aggregated map`
    );
  }
});

test("design-system/tokens — aggregated tokens.chartPalette is the same reference", () => {
  assert.equal(tokens.chartPalette, chartPalette);
});

test("design-system/tokens — aggregated tokens.regimeColors.bullish matches direct import", () => {
  assert.equal(tokens.regimeColors.bullish, regimeColors.bullish);
});

// ─────────────────────────────────────────────────────────────────────────────
// 13. Shadows
// ─────────────────────────────────────────────────────────────────────────────
test("design-system/tokens — shadow tokens are non-empty CSS strings", () => {
  const shadowValues = Object.values(shadows);
  assert.ok(shadowValues.length >= 4, "must have at least 4 shadow tokens");
  for (const s of shadowValues) {
    assert.equal(typeof s, "string");
    assert.ok(s.length > 0, "shadow must be non-empty");
    // All shadows must contain rgba
    assert.ok(
      s.includes("rgba") || s.includes("rgb"),
      `shadow "${s.substring(0, 40)}" must use rgba/rgb`
    );
  }
});

test("design-system/tokens — glassmorphism shadow contains inset", () => {
  assert.ok(shadows.glass.includes("inset"), "glass shadow must contain inset highlight");
});

// ─────────────────────────────────────────────────────────────────────────────
// 14. Radius Tokens
// ─────────────────────────────────────────────────────────────────────────────
test("design-system/tokens — radius.full is 9999px (pill shape)", () => {
  assert.equal(radius.full, "9999px");
});

test("design-system/tokens — radius tokens ordered sm < base < md < lg < xl", () => {
  const toRem = (s: string) => parseFloat(s);
  const ordered = [radius.sm, radius.base, radius.md, radius.lg, radius.xl].map(toRem);
  for (let i = 1; i < ordered.length; i++) {
    assert.ok(ordered[i] > ordered[i - 1], `radius[${i}] must be > radius[${i - 1}]`);
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// 15. Foreground Tokens
// ─────────────────────────────────────────────────────────────────────────────
test("design-system/tokens — foreground tokens are hex or rgba strings", () => {
  const fgValues = Object.values(foreground);
  for (const v of fgValues) {
    assert.ok(
      v.startsWith("#") || v.startsWith("rgba") || v.startsWith("rgb"),
      `foreground token "${v}" must be a color`
    );
  }
});
