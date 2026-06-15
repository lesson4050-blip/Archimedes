/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // TODO(phase-2): remove output:export when adding API routes proxy to FastAPI
  // Temporary decision for Phase 1 — required for Capacitor (webDir:'out') and Tauri static builds
  // See docs/DECISIONS.md ADR-009
  output: process.env.NODE_ENV === 'production' ? 'export' : undefined,
  images: {
    dangerouslyAllowSVG: true,
    contentDispositionType: 'attachment',
    unoptimized: true,
  },
};

module.exports = nextConfig;
