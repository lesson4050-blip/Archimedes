# Archimedes — Platform Support

---

## Support Matrix

| Platform | Target | Phase | Notes |
|----------|--------|-------|-------|
| Windows 10/11 | x64, ARM64 | Phase 1 | Tauri v2 |
| macOS 12+ | Intel, Apple Silicon | Phase 1 | Tauri v2 |
| Ubuntu 20.04+ | x64, ARM64 | Phase 1 | Tauri v2 |
| Android 8.0+ | arm64-v8a | Phase 7 | Capacitor |
| iOS 16.0+ | arm64 | Phase 7 | Capacitor |
| Web (modern browsers) | All | Phase 1 | Next.js |
| CLI | Linux/macOS/Windows | Phase 1 | Python 3.11+ |

---

## Desktop (Tauri v2)

### Why Tauri v2
- ~10MB bundle vs ~150MB Electron
- Rust security model — no Node.js in production binary
- System webview (OS browser engine, no bundled Chromium)
- Strong IPC model for native OS calls

### Architecture

```
desktop/
├── src/              # React + TypeScript frontend
│   ├── App.tsx
│   ├── components/
│   └── lib/
│       └── api.ts    # WebSocket client
└── src-tauri/        # Rust backend
    ├── src/
    │   ├── main.rs
    │   └── commands.rs
    └── tauri.conf.json
```

### WebSocket Client

```typescript
// lib/api.ts
const WS_URL = import.meta.env.VITE_WS_URL ?? 'ws://localhost:8000/ws';

export class ArchimedesClient {
  private ws: WebSocket | null = null;

  connect(sessionId: string) {
    this.ws = new WebSocket(`${WS_URL}/${sessionId}`);
    this.ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      this.handleMessage(msg);
    };
  }

  send(message: string) {
    this.ws?.send(JSON.stringify({ type: 'task', payload: { message } }));
  }

  private handleMessage(msg: unknown) {
    // dispatch to UI state
  }
}
```

### Build Commands

```bash
cd desktop && npm run tauri dev          # development
npm run tauri build                       # current platform
npm run tauri build -- --target x86_64-pc-windows-msvc
npm run tauri build -- --target aarch64-apple-darwin
npm run tauri build -- --target x86_64-unknown-linux-gnu
```

---

## Mobile (Capacitor)

### Why Capacitor
- Shares React components with web app
- Native API access via plugins
- No React Native bridge complexity
- Community plugins cover core needs

### Config

```typescript
// capacitor.config.ts
import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.archimedes.app',
  appName: 'Archimedes',
  webDir: 'dist',
  server: {
    url: process.env.NODE_ENV === 'development'
      ? 'http://localhost:3000'
      : undefined,
    cleartext: true,
  },
  plugins: {
    SplashScreen: {
      launchShowDuration: 1000,
      backgroundColor: '#0f172a',
    },
  },
};
export default config;
```

### Build Commands

```bash
cd mobile && npm run build
npx cap sync
npx cap open android    # Android Studio
npx cap open ios        # Xcode (macOS only)
npx cap run android
npx cap run ios
```

---

## Platform Detection

```typescript
// lib/platform.ts
import { Capacitor } from '@capacitor/core';

export type Platform = 'web' | 'ios' | 'android' | 'desktop';

export function getPlatform(): Platform {
  if (typeof window !== 'undefined' && '__TAURI__' in window) return 'desktop';
  const cap = Capacitor.getPlatform();
  if (cap === 'ios') return 'ios';
  if (cap === 'android') return 'android';
  return 'web';
}

export const isNative = () => Capacitor.isNativePlatform();
export const isMobile = () => ['ios', 'android'].includes(getPlatform());
export const isDesktop = () => getPlatform() === 'desktop';
export const isWeb = () => getPlatform() === 'web';
```

---

## CI/CD

```yaml
# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -r requirements.txt
      - run: pytest --cov=app tests/
      - run: mypy app/ --strict

  web:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20' }
      - run: cd web && npm ci && npm run build && npm run lint && npm run typecheck

  desktop:
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable
      - uses: actions/setup-node@v4
        with: { node-version: '20' }
      - run: cd desktop && npm ci && npm run tauri build
```
