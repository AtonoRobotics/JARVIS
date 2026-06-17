# JARVIS fork maintenance — keeping the rebrand across upstream updates

This repo is a **rebrand fork of upstream Hermes**. The JARVIS look (dark
"Glassify" theme, modern typography, redesigned shell) lives on top of
upstream files, so pulling updates can clobber it if you don't follow a fork
workflow. This doc explains how to keep the customizations durable.

## TL;DR

1. **Merge upstream in — never `reset --hard` or re-clone.** A merge keeps
   your work; a hard reset throws it away unconditionally.
2. **Run the one-time setup below** in every clone (these git settings can't
   be committed).
3. **After bumping `@nous-research/ui`, re-verify the override anchors** (the
   DS variable/class names our overrides hook into).

## One-time setup (run once per clone)

These configure git locally; they are intentionally *not* committed, so each
working copy needs them:

```bash
# Remember how you resolve a conflict and auto-replay it next time.
# Huge for the recurring conflicts in App.tsx / index.css / presets.ts.
git config rerere.enabled true

# Enable the `merge=ours` driver referenced by .gitattributes, so brand-only
# files always keep our version on conflict.
git config merge.ours.driver true

# Add upstream Hermes as a remote (only if not already present).
git remote add upstream <UPSTREAM_HERMES_GIT_URL>
```

## Update workflow

```bash
git fetch upstream
git checkout main                  # your JARVIS main
git merge upstream/main            # MERGE — do not reset/clone
# resolve any conflicts (see the file map below), then:
cd web && npm install && npm run build   # re-verify the UI still builds
```

If you hit the same conflicts every update, `rerere` will replay your prior
resolution automatically after the first time — just confirm and continue.

## Where the JARVIS customizations live

The redesign was deliberately refactored so most of it sits in **dedicated
files upstream never touches** (zero merge conflicts), leaving only small
hooks in shared files.

### Brand-only files (never conflict — upstream has no copy)

| File | What it holds |
|---|---|
| `web/src/jarvis-overrides.css` | All brand global CSS: `font-display` utility, font-var remap (retiring the pixel faces), document antialiasing, rounded `bg-card` surfaces. |
| `web/src/themes/jarvis-glassify.ts` | The entire Glassify brand theme (palette, typography, frosted-glass `customCSS`). Self-contained. |

Add new brand-level CSS / theme code to **these** files, not to shared ones.

### Shared files with small JARVIS hooks (may conflict; resolve by keeping both)

| File | JARVIS footprint |
|---|---|
| `web/src/index.css` | One `@import './jarvis-overrides.css'` line. |
| `web/src/themes/presets.ts` | One import of `glassifyTheme` + one entry in `BUILTIN_THEMES`. |
| `web/src/themes/context.tsx` | Default theme selection. |
| `web/src/App.tsx` | Shell / sidebar redesign + brand lockup. **Largest conflict surface** — `rerere` helps most here. |
| `web/src/contexts/PageHeaderProvider.tsx` | Page-header type + frosted bar. |
| `web/index.html` | Page title. |
| `web/src/i18n/*.ts` | Brand name strings. |
| `hermes_cli/web_server.py` | `glassify` listed in `_BUILTIN_DASHBOARD_THEMES` (keep in sync with `presets.ts`). |

## Updating the design system (`@nous-research/ui`)

`web/package.json` pins the DS to an **exact** version (e.g. `0.18.2`, no
`^`), so `npm update` cannot bump it. A DS update does **not** overwrite the
files above — but it *can silently break* the overrides if the DS renames the
names they hook into. After any deliberate DS bump, re-verify these anchors
still exist (or update the overrides to match):

- Font CSS vars: `--font-mondwest`, `--font-rules-expanded`,
  `--font-rules-compressed` (remapped in `jarvis-overrides.css`).
- Surface class: `bg-card` (rounded + frosted).
- `text-display` utility (uppercase + tracking) and the `font-mondwest` /
  `font-expanded` / `font-compressed` utilities.

A quick `npm run build` + a visual check of a page (fonts not pixelated,
cards rounded/frosted) confirms the overrides still apply.
