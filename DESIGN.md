# DESIGN.md - Dip Mafia dashboard

Design system for the unified dashboard (`docs/index.html`). Hand-authored, no framework, no chart library.

## Identity

"Dip Mafia, an almanac of hindsight." A precise dark instrument with editorial restraint: terminal/ledger lineage, one warm signal accent, strict performance semantics. Not generic SaaS, not the AI cream default, not the old purple Chart.js look.

## Color (OKLCH)

Strategy: **Restrained + one Committed accent.** Cool near-black canvas, warm amber brand accent for primary/active/selection only, strict green/red reserved for performance.

```
--bg:        oklch(0.165 0.012 250)   /* cool near-black canvas */
--surface:   oklch(0.205 0.014 250)   /* cards, panels */
--surface-2: oklch(0.250 0.016 250)   /* raised / hover / header */
--line:      oklch(0.300 0.014 250)   /* hairlines */
--line-2:    oklch(0.380 0.014 250)   /* stronger dividers */
--ink:       oklch(0.965 0.004 250)   /* primary text */
--ink-dim:   oklch(0.760 0.010 250)   /* secondary text  (>=4.5:1 on bg) */
--ink-mute:  oklch(0.600 0.012 250)   /* labels, axes     (large/again-bg only) */
--accent:    oklch(0.800 0.130 75)    /* amber: brand, primary, active, selection */
--accent-2:  oklch(0.700 0.120 70)    /* amber pressed / dim */
--up:        oklch(0.760 0.150 155)   /* gains (green) */
--down:      oklch(0.680 0.175 25)    /* losses (red) */
--sip:       oklch(0.740 0.100 220)   /* SIP series (blue) */
--bench:     oklch(0.680 0.020 250)   /* NIFTY / benchmark (slate, dashed) */
```

Accent is never used for decoration or inactive states. Gains/losses use `--up`/`--down` only. Series colors: Timed HODL = accent, SIP = `--sip`, NIFTY = `--bench` dashed.

## Type

Three roles, no overlap (display never labels UI):
- **Inter** - all UI, nav, labels, body, headings via weight. Fixed rem scale.
- **JetBrains Mono** - every figure (tabular-nums), axes, tickers, the horizon control.
- **Fraunces** (display, sparse) - wordmark + the single Overview hero number only.

Scale (fixed, ratio ~1.2): 0.68 / 0.75 / 0.82 / 0.92 / 1.0 / 1.15 / 1.5 / 2.2 / 3.4 rem. Hero capped well under 6rem.

## Layout

- Sticky top bar: wordmark · section nav · global horizon segmented control. Collapses on mobile (nav becomes a select / horizontal scroll; horizon stays).
- One section visible at a time (SPA switch, no reload). Overview is default.
- Content grid: `repeat(auto-fit, minmax(min(100%, 320px), 1fr))`; hero/wide charts span full.
- Spacing scale 4/8/12/16/24/32/48. Vary for rhythm; cards only where they are the right affordance, never nested.

## Components

Segmented control (nav + horizon), stat tile, **lead tile** (the one headline metric per section: raised `--surface-2`, spans 2 grid cols, figure at 2.7rem/700 vs the 1.6rem/600 of regular tiles - this size+weight jump is the hierarchy spine, deliberately breaking the uniform grid), chart panel, data table (sticky head, hover row, sortable), pill/tag, tooltip+crosshair, donut legend, comparison table (best-per-row highlight). Figures lead: mono, tabular, weight 600-700, tight tracking; labels stay quiet (mono, uppercase, `--ink-mute`). The Overview hero number is the single largest element (Fraunces, clamp to 5.4rem, well under 6) with `₹` and `Cr`/`L` rendered as muted superscript affixes so the digits dominate. Each interactive element: default / hover / focus-visible / active / disabled. Empty + loading states. Motion 150-250ms ease-out; horizon/section changes cross-fade; charts draw-in once (reduced-motion: instant). No page-load choreography.

## Charts (hand-built SVG)

One small module: `lineArea` (multi-series, optional fill, hover crosshair+tooltip, draw-in), `bars` (vertical/horizontal, grouped), `donut`. Tabular mono axes, `--line` grid, series colors above. Equity/NAV/drawdown get hover; secondary charts static.
