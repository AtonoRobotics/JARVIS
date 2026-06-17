import type { DashboardTheme } from "./types";

/**
 * JARVIS · Glassify — the signature brand theme.
 *
 * Kept in its own file (not in the upstream `presets.ts`) so that merging
 * updates from upstream Hermes never conflicts with the brand theme. The
 * only footprint in the shared `presets.ts` is a one-line import and a
 * one-line entry in `BUILTIN_THEMES`. This file is intentionally
 * self-contained — it inlines the system font stacks rather than importing
 * shared presets constants, so upstream changes to those constants can't
 * silently alter the brand look.
 *
 * A dark, modern-luxury reskin: smoked near-black glass canvas, a warm
 * platinum/champagne midground, and a gold accent that drives primary
 * actions and focus rings. The "glass" comes from two cooperating layers:
 *
 *   1. `colorOverrides` make every elevated surface (card, popover,
 *      secondary, muted, accent) *translucent* — they're authored as
 *      `color-mix(... transparent)` instead of opaque so what's behind
 *      them shows through.
 *   2. `customCSS` adds the frost: `backdrop-filter: blur()` on those
 *      same surfaces plus the header/sidebar chrome, with a soft inner
 *      highlight + deep drop shadow so panels read as lifted glass.
 *
 * Larger `radius` (1rem) keeps panel corners soft, and the low
 * `noiseOpacity` keeps the canvas sleek rather than gritty.
 */

const SYSTEM_SANS =
  'system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif';
const SYSTEM_MONO =
  'ui-monospace, "SF Mono", "Cascadia Mono", Menlo, Consolas, monospace';

export const glassifyTheme: DashboardTheme = {
  name: "glassify",
  label: "JARVIS Glass",
  description: "Dark modern luxury — frosted glass surfaces and champagne accents",
  palette: {
    background: { hex: "#0a0b0f", alpha: 1 },
    midground: { hex: "#e8e2d4", alpha: 1 },
    foreground: { hex: "#ffffff", alpha: 0 },
    warmGlow: "rgba(201, 168, 106, 0.22)",
    noiseOpacity: 0.35,
  },
  typography: {
    baseSize: "15px",
    lineHeight: "1.55",
    fontSans: `"Inter", ${SYSTEM_SANS}`,
    fontDisplay: `"Manrope", "Inter", ${SYSTEM_SANS}`,
    fontMono: `"JetBrains Mono", ${SYSTEM_MONO}`,
    fontUrl:
      "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap",
    letterSpacing: "-0.01em",
  },
  layout: {
    radius: "1rem",
    density: "comfortable",
  },
  terminalBackground: "#0a0b0f",
  colorOverrides: {
    // Translucent so the backdrop-filter blur below actually has something
    // to frost. Authored against the base hex + transparent rather than
    // the opaque DS cascade defaults.
    card: "color-mix(in srgb, var(--background-base) 52%, transparent)",
    popover: "color-mix(in srgb, var(--background-base) 82%, transparent)",
    secondary: "color-mix(in srgb, var(--midground-base) 8%, transparent)",
    muted: "color-mix(in srgb, var(--midground-base) 10%, transparent)",
    accent: "color-mix(in srgb, #c9a86a 18%, transparent)",
    border: "color-mix(in srgb, var(--midground-base) 13%, transparent)",
    input: "color-mix(in srgb, var(--midground-base) 13%, transparent)",
    // Champagne gold accent for primary actions + focus rings.
    primary: "#c9a86a",
    primaryForeground: "#0a0b0f",
    ring: "#c9a86a",
    warning: "#e0b352",
  },
  seriesColors: {
    inputTokenAccent: "#e8e2d4",
    outputTokenAccent: "#c9a86a",
  },
  swatchColors: ["#0a0b0f", "#c9a86a", "#e8e2d4"],
  customCSS: `
/* ────────────────────────────────────────────────────────────────
   JARVIS · Glassify — frosted glass chrome + champagne luxe accents
   ──────────────────────────────────────────────────────────────── */

/* Frost every elevated surface. Translucency comes from colorOverrides;
   this adds the blur, a lifted drop shadow, and a hairline top highlight
   so panels read as a pane of smoked glass rather than a flat fill. */
.bg-card,
.bg-popover,
.bg-secondary,
.bg-muted {
  backdrop-filter: blur(18px) saturate(150%);
  -webkit-backdrop-filter: blur(18px) saturate(150%);
  box-shadow:
    0 12px 40px -14px rgba(0, 0, 0, 0.7),
    inset 0 1px 0 color-mix(in srgb, var(--midground-base) 14%, transparent);
}

/* Header + sidebar nav float over scrolling content with a deeper frost. */
header,
aside {
  backdrop-filter: blur(24px) saturate(140%);
  -webkit-backdrop-filter: blur(24px) saturate(140%);
}

/* Champagne sheen on the primary action so gold buttons read as polished
   metal rather than a flat swatch. */
.bg-primary {
  background-image: linear-gradient(
    180deg,
    color-mix(in srgb, #ffffff 22%, transparent) 0%,
    transparent 55%
  );
}
`,
};
