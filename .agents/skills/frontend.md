# Skill: Frontend — Next.js + Design System

## Trigger
Use when working on anything in web/, components, pages, UI, layout, styles,
or any TypeScript/React code in the Archimedes web app.

---

## Our Frontend Stack

```
web/
├── app/                    # Next.js 15 App Router
│   ├── layout.tsx          # Root layout (metadata, fonts, providers)
│   ├── page.tsx            # Home → redirects to /chat
│   └── chat/
│       └── [sessionId]/
│           └── page.tsx    # Chat interface
├── components/
│   ├── ui/                 # Primitives (Button, Card, Input, Badge)
│   ├── chat/               # ChatInput, MessageList, MessageBubble, ToolCallBlock
│   └── layout/             # Sidebar, Header, ThemeProvider
├── lib/
│   ├── websocket.ts        # useWebSocket hook
│   ├── api.ts              # REST client (fetch wrapper)
│   └── platform.ts         # getPlatform(), isMobile(), isDesktop()
└── public/                 # Static assets (icons already generated)
```

Stack: Next.js 15 + React 18 + TypeScript strict + Tailwind CSS + Radix UI + Framer Motion

---

## Design System Tokens (use these, never invent values)

### Colors — use Tailwind classes, never hex directly in JSX

```
Background:   bg-slate-900      (#0f172a)  ← app background
Surface:      bg-slate-800      (#1e293b)  ← cards, panels
Elevated:     bg-slate-700      (#334155)  ← popovers, dropdowns
Primary:      bg-indigo-500     (#6366f1)  ← actions, CTAs
Primary hover:bg-indigo-600     (#4f46e5)

Text primary:   text-slate-50   (#f8fafc)
Text secondary: text-slate-400  (#94a3b8)
Text muted:     text-slate-600  (#475569)

Success: text-green-400 / bg-green-500/10 / border-green-500/20
Warning: text-amber-400 / bg-amber-500/10 / border-amber-500/20
Error:   text-red-400   / bg-red-500/10   / border-red-500/20
Info:    text-blue-400  / bg-blue-500/10  / border-blue-500/20
```

### Typography — Inter font, 16px base

```
text-sm   = 14px  secondary content
text-base = 16px  default
text-lg   = 18px  subheadings
text-2xl  = 22px  card titles
text-3xl  = 28px  section headers

font-mono = JetBrains Mono  (code, terminal output)
```

### Spacing — multiples of 4px only

```
p-1 = 4px    p-2 = 8px    p-4 = 16px (base)
p-6 = 24px   p-8 = 32px   p-12 = 48px
```

---

## Component Patterns (copy these exactly)

### Button

```tsx
// Primary
<button className="px-4 py-2 bg-indigo-500 hover:bg-indigo-600 text-white font-medium text-sm rounded-lg transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:ring-offset-slate-900 disabled:opacity-50 disabled:cursor-not-allowed">
  Send
</button>

// Ghost
<button className="px-4 py-2 bg-transparent hover:bg-slate-700 text-slate-300 hover:text-white font-medium text-sm border border-slate-700 rounded-lg transition-all duration-150">
  Cancel
</button>

// Danger
<button className="px-4 py-2 bg-red-500/10 hover:bg-red-500/20 text-red-400 font-medium text-sm border border-red-500/20 rounded-lg transition-all duration-150">
  Delete
</button>
```

### Card

```tsx
<div className="bg-slate-800 border border-slate-700 rounded-xl p-6 hover:border-indigo-500/30 transition-colors duration-200">
  {children}
</div>
```

### Input

```tsx
<input
  className="w-full px-4 py-2.5 bg-slate-900 border border-slate-700 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 text-slate-100 placeholder:text-slate-500 text-sm rounded-lg outline-none transition-colors duration-150"
  placeholder="Message Archimedes..."
/>
```

### Status Badge

```tsx
const badgeVariants = {
  running: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  success: "bg-green-500/10 text-green-400 border-green-500/20",
  error:   "bg-red-500/10 text-red-400 border-red-500/20",
  pending: "bg-amber-500/10 text-amber-400 border-amber-500/20",
} as const

<span className={`px-2 py-0.5 text-xs font-medium rounded-full border ${badgeVariants[status]}`}>
  {label}
</span>
```

### Chat Messages

```tsx
// User message (right-aligned)
<div className="flex justify-end">
  <div className="max-w-[80%] px-4 py-3 bg-indigo-600 rounded-2xl rounded-tr-sm text-white text-sm leading-relaxed">
    {content}
  </div>
</div>

// Agent message (left-aligned)
<div className="flex justify-start">
  <div className="max-w-[80%] px-4 py-3 bg-slate-800 border border-slate-700 rounded-2xl rounded-tl-sm text-slate-100 text-sm leading-relaxed">
    {content}
  </div>
</div>
```

### Code Block (terminal output, tool results)

```tsx
<pre className="bg-slate-950 border border-slate-800 rounded-lg p-4 overflow-x-auto text-sm font-mono text-slate-200 leading-relaxed">
  <code>{output}</code>
</pre>
```

### Glassmorphism Panel (floating overlays only)

```tsx
<div className="bg-slate-800/70 backdrop-blur-md border border-indigo-500/20 rounded-xl">
  {children}
</div>
```

---

## WebSocket Hook (use this, don't rewrite it)

```typescript
// lib/websocket.ts
import { useEffect, useRef, useState, useCallback } from "react"

type WSStatus = "connecting" | "open" | "closed" | "error"

interface WSMessage {
  type: "stream" | "tool_call" | "tool_result" | "done" | "error"
  session_id: string
  payload: Record<string, unknown>
}

export function useWebSocket(sessionId: string) {
  const ws = useRef<WebSocket | null>(null)
  const [messages, setMessages] = useState<WSMessage[]>([])
  const [status, setStatus] = useState<WSStatus>("connecting")

  useEffect(() => {
    const token = localStorage.getItem("archimedes_token") ?? ""
    const url = `${process.env.NEXT_PUBLIC_WS_URL}/${sessionId}?token=${token}`

    ws.current = new WebSocket(url)
    ws.current.onopen = () => setStatus("open")
    ws.current.onclose = () => setStatus("closed")
    ws.current.onerror = () => setStatus("error")
    ws.current.onmessage = (e: MessageEvent) => {
      const msg = JSON.parse(e.data as string) as WSMessage
      setMessages((prev) => [...prev, msg])
    }

    return () => {
      ws.current?.close()
    }
  }, [sessionId])

  const send = useCallback((message: string) => {
    if (ws.current?.readyState !== WebSocket.OPEN) return
    ws.current.send(
      JSON.stringify({
        type: "task",
        session_id: sessionId,
        payload: { message },
      })
    )
  }, [sessionId])

  return { messages, send, status }
}
```

---

## Animation Rules

- Transitions: `duration-150` for micro (hover/focus), `duration-200` for default
- Easing: `ease-in-out` for most, `ease-out` for entrances
- Framer Motion: only for complex sequences (streaming text reveal, panel slides)
- Always include: `@media (prefers-reduced-motion: reduce)` support via Tailwind `motion-reduce:` prefix

```tsx
// Streaming text reveal with Framer Motion
<motion.span
  initial={{ opacity: 0 }}
  animate={{ opacity: 1 }}
  transition={{ duration: 0.15 }}
  className="motion-reduce:transition-none"
>
  {delta}
</motion.span>
```

---

## TypeScript Rules (strict mode — no exceptions)

```typescript
// ❌ NEVER
const handler = (data: any) => { ... }
const result = response as SomeType

// ✅ ALWAYS
const handler = (data: unknown): void => {
  if (!isWSMessage(data)) return
  // use data safely
}

// Type guards over casting
function isWSMessage(val: unknown): val is WSMessage {
  return (
    typeof val === "object" &&
    val !== null &&
    "type" in val &&
    "session_id" in val
  )
}

// Explicit return types on all exported functions
export function formatTimestamp(date: Date): string {
  return date.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" })
}
```

---

## File Naming Conventions

```
components/ui/Button.tsx        PascalCase for components
components/chat/MessageList.tsx
lib/websocket.ts                camelCase for utilities
app/chat/[sessionId]/page.tsx   Next.js conventions
```

---

## Rules

- Never use inline styles — Tailwind only
- Never use hex colors directly in className — use Tailwind tokens from Design System
- Never use `any` — use `unknown` + type guards
- Never use `useEffect` for data fetching — use `useWebSocket` hook or React Query
- All images via `next/image`, not `<img>`
- Scrollbar styling: always add custom scrollbar CSS (see DESIGN_SYSTEM.md)
- Icons: Lucide React only (14px inline, 16px buttons, 20px headers, 24px hero)
- No hardcoded strings — move to constants or i18n keys
- Component files export ONE default component matching the filename
