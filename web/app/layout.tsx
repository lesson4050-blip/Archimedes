import type { Metadata } from "next"
import { Inter } from "next/font/google"
import { ThemeProvider } from "@/components/layout/ThemeProvider"
import "./globals.css"

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
})

export const metadata: Metadata = {
  title: "Archimedes",
  description: "Autonomous AI agent platform",
  icons: {
    icon: [
      { url: "/favicon.ico", sizes: "any" },
      { url: "/favicon-16x16.png", sizes: "16x16", type: "image/png" },
      { url: "/favicon-32x32.png", sizes: "32x32", type: "image/png" },
    ],
    apple: [
      { url: "/apple-touch-icon.png", sizes: "180x180", type: "image/png" },
    ],
    other: [
      { rel: "android-chrome", url: "/android-chrome-192x192.png", sizes: "192x192" },
      { rel: "android-chrome-512", url: "/android-chrome-512x512.png", sizes: "512x512" },
    ],
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}): React.JSX.Element {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.variable} font-sans antialiased bg-slate-900 text-slate-50 min-h-screen`}>
        <ThemeProvider attribute="class" defaultTheme="dark">
          {children}
        </ThemeProvider>
      </body>
    </html>
  )
}
