# Archimedes — Design System

> Version: 1.0 | Framework: Tailwind CSS + Radix UI

---

## Philosophy

Dark, focused, powerful. UI surfaces agent activity without visual noise.

**Principles:**
1. Dark by default — reduces eye strain during long sessions
2. Information density over decoration — no gratuitous animation
3. Progressive disclosure — complexity hidden until needed
4. Accessibility first — WCAG 2.1 AA minimum

---

## Color Palette

### Brand

| Token | Hex | Tailwind | Usage |
|-------|-----|----------|-------|
| primary | #6366f1 | indigo-500 | Actions, links, active state |
| primary-hover | #4f46e5 | indigo-600 | Hover on primary elements |
| primary-subtle | #312e81 | indigo-900 | Tinted backgrounds |

### Background

| Token | Hex | Tailwind | Usage |
|-------|-----|----------|-------|
| bg-base | #0f172a | slate-900 | App background |
| bg-surface | #1e293b | slate-800 | Cards, panels |
| bg-elevated | #334155 | slate-700 | Popovers, dropdowns |

### Text

| Token | Hex | Tailwind | Usage |
|-------|-----|----------|-------|
| text-primary | #f8fafc | slate-50 | Primary content |
| text-secondary | #94a3b8 | slate-400 | Secondary / metadata |
| text-muted | #475569 | slate-600 | Disabled, placeholder |

### Semantic

| Token | Hex | Tailwind | Usage |
|-------|-----|----------|-------|
| success | #22c55e | green-500 | Task complete |
| warning | #f59e0b | amber-500 | Pending, rate limit |
| error | #ef4444 | red-500 | Errors, failures |
| info | #3b82f6 | blue-500 | Info messages |

### Tailwind Config Extension

```js
// tailwind.config.ts
colors: {
  primary: '#6366f1',
  'primary-hover': '#4f46e5',
  'bg-base': '#0f172a',
  'bg-surface': '#1e293b',
  'bg-elevated': '#334155',
}
```

---

## Typography

### Font Stack

```css
font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
font-family-mono: 'JetBrains Mono', 'Fira Code', monospace;
```

### Scale

| Name | Size | Weight | Usage |
|------|------|--------|-------|
| display | 36px | 700 | Page titles |
| heading-1 | 28px | 600 | Section headers |
| heading-2 | 22px | 600 | Card titles |
| body | 16px | 400 | Default content |
| body-sm | 14px | 400 | Secondary content |
| caption | 12px | 400 | Labels, metadata |
| code | 14px | 400 | Monospace |

---

## Spacing

Base unit: 8px. All spacing is multiples of 4px.

```
4px  = space-1
8px  = space-2
16px = space-4  (base)
24px = space-6
32px = space-8
48px = space-12
64px = space-16
```

---

## Animations

Rule: Motion conveys meaning, not decoration.

| Type | Duration | Easing | Usage |
|------|----------|--------|-------|
| Micro | 100-150ms | ease-out | Hover, focus, icon |
| Default | 200ms | ease-in-out | Panel, tabs |
| Entrance | 300ms | ease-out | Modal appear |
| Exit | 200ms | ease-in | Modal dismiss |

Always include reduced-motion support:
```css
@media (prefers-reduced-motion: reduce) {
  * { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; }
}
```

---

## Effects

### Glassmorphism

Use for floating panels on top of content.

```
Tailwind: bg-slate-800/70 backdrop-blur-md border border-indigo-500/20
```

### Gradients

```css
/* Primary (buttons, accents) */
background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);

/* Glow (active elements) */
box-shadow: 0 0 20px rgba(99, 102, 241, 0.3);
```

### Scrollbar

```css
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #0f172a; }
::-webkit-scrollbar-thumb { background: #334155; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #6366f1; }
```

---

## Components

### Button

```tsx
// Primary
className="px-4 py-2 bg-indigo-500 hover:bg-indigo-600 text-white font-medium text-sm rounded-lg transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:ring-offset-slate-900 disabled:opacity-50 disabled:cursor-not-allowed"

// Ghost
className="px-4 py-2 bg-transparent hover:bg-slate-700 text-slate-300 hover:text-white font-medium text-sm border border-slate-700 rounded-lg transition-all duration-150"

// Danger
className="px-4 py-2 bg-red-500/10 hover:bg-red-500/20 text-red-400 font-medium text-sm border border-red-500/20 rounded-lg transition-all duration-150"
```

### Card

```tsx
className="bg-slate-800 border border-slate-700 rounded-xl p-6 hover:border-indigo-500/30 transition-colors duration-200"
```

### Input

```tsx
className="w-full px-4 py-2.5 bg-slate-900 border border-slate-700 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 text-slate-100 placeholder:text-slate-500 text-sm rounded-lg outline-none transition-colors duration-150"
```

### Chat Messages

```tsx
// User
className="max-w-[80%] px-4 py-3 bg-indigo-600 rounded-2xl rounded-tr-sm text-white text-sm"

// Agent
className="max-w-[80%] px-4 py-3 bg-slate-800 border border-slate-700 rounded-2xl rounded-tl-sm text-slate-100 text-sm"
```

### Status Badge

```tsx
const variants = {
  running:  "bg-blue-500/10 text-blue-400 border-blue-500/20",
  success:  "bg-green-500/10 text-green-400 border-green-500/20",
  error:    "bg-red-500/10 text-red-400 border-red-500/20",
  pending:  "bg-amber-500/10 text-amber-400 border-amber-500/20",
}
className={`px-2 py-0.5 text-xs font-medium rounded-full border ${variants[status]}`}
```

### Code Block

```tsx
className="bg-slate-950 border border-slate-800 rounded-lg p-4 overflow-x-auto text-sm font-mono text-slate-200 leading-relaxed"
```

---

## Icons

Lucide React. Size conventions:
- 14px — inline with text
- 16px — buttons, list items
- 20px — section headers
- 24px — hero elements

---

## Breakpoints

```
sm:  640px   tablet portrait
md:  768px   tablet landscape
lg:  1024px  desktop
xl:  1280px  large desktop
2xl: 1536px  ultrawide
```

Mobile-first: default = mobile. Breakpoint prefixes = scale up.
