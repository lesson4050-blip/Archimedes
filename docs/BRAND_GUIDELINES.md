# Archimedes — Brand Guidelines

> **Version:** 1.0.0  
> **Status:** Released  
> **Updated:** June 2026

Welcome to the official brand guidelines for **Archimedes**, an open-source, autonomous AI agent platform. This document outlines the visual elements, assets, and styling rules to maintain consistency across Web, Desktop, and Mobile surfaces.

---

## 1. Brand Philosophy

Archimedes stands for clarity, efficiency, and full developer autonomy. The visual design system reflects a **dark, focused, and powerful** developer environment, prioritizing code-act activities, streaming outputs, and clean, high-contrast layouts.

---

## 2. Logo Assets

The Archimedes logo consists of a vertical DNA double helix (the Symbol) and the wordmark "archimedes" (the Logotype). All assets are stored under [assets/logos/](../assets/logos/).

| Asset | Description | Viewport | Usage |
|---|---|---|---|
| [logo-full.svg](../assets/logos/logo-full.svg) | Full logo (Helix + Wordmark) | 878x666 | Main headers, splash screens, landing page. |
| [logo-icon.svg](../assets/logos/logo-icon.svg) | Symbol only (DNA Helix) | 542x542 (Square) | App launcher icon, favicons, avatars, sizes < 64px. |
| [logo-full-white.svg](../assets/logos/logo-full-white.svg) | Full logo (Inverted White) | 878x666 | Dark backgrounds (Slate-900 / Slate-800). |
| [logo-icon-white.svg](../assets/logos/logo-icon-white.svg) | Symbol only (Inverted White) | 542x542 (Square) | App launcher icon for dark UI elements. |

> [!IMPORTANT]
> **Readability Constraint:** For all rendering sizes **below 64px**, the text wordmark becomes unreadable. In these instances, you **MUST** use the symbol-only version (`logo-icon.svg` or `logo-icon-white.svg`).

---

## 3. Color Palette

Our color system is divided into brand accent colors, neutral grays, and status-indicating semantical colors.

### Brand Accent
- **Primary Indigo (`#6366f1` / `indigo-500`):** Used for primary action buttons, links, active tab indicator, and round app icon background borders.
- **Primary Hover (`#4f46e5` / `indigo-600`):** State transitions for buttons and links.
- **Primary Subtle (`#312e81` / `indigo-900`):** Used for background highlights and card borders.

### Background & Surface
- **Base Background (`#0f172a` / `slate-900`):** Used for main background. Used as the solid background for iOS AppIcon.
- **Surface Background (`#1e293b` / `slate-800`):** Used for cards, panels, popovers, and sidebars.

### Text Hierarchy
- **Text Primary (`#f8fafc` / `slate-50`):** High contrast headings, buttons, and primary content.
- **Text Secondary (`#94a3b8` / `slate-400`):** Body text, labels, and secondary context.

---

## 4. Clear Space and Alignment

To ensure visibility and impact, the logo must always have a minimum clear space surrounding it.
- **Master Logo (`logo-full.svg`):** Maintain a clear space equal to at least 10% of the logo's width on all sides.
- **App Icons:** Standard app launcher icons have a built-in 15% padding from the boundaries of the square/circle to avoid clipping on rounded screens (iOS and Android adaptive grids).

```
  ┌─────────────────────────┐
  │      Clear Space        │
  │   ┌───────────────┐     │
  │   │  ▲         ▲  │     │
  │   │  │  Helix  │  │     │
  │   │  ▼         ▼  │     │
  │   │  Wordmark     │     │
  │   └───────────────┘     │
  └─────────────────────────┘
```

---

## 5. Typography

The default typography stack is built for coding readability:
- **UI Fonts:** `'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif`
- **Monospace Fonts:** `'JetBrains Mono', 'Fira Code', monospace`

---

## 6. Incorrect Usage

To maintain brand integrity, avoid the following misuses:
1. **Never** stretch, squish, or deform the aspect ratio of the logo.
2. **Never** use the full logo (including text) at sizes under 64px.
3. **Never** render the logo with a transparent background on iOS (must use a solid `#0f172a` or `#6366f1` background).
4. **Never** use saturated background colors other than the brand palette (Indigo or Slate) for logos.
