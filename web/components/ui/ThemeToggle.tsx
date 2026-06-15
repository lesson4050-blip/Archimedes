'use client'

import { useEffect, useState } from "react"
import { useTheme } from "next-themes"
import { Sun, Moon } from "lucide-react"

export default function ThemeToggle(): React.JSX.Element | null {
  const [mounted, setMounted] = useState(false)
  const { resolvedTheme, setTheme } = useTheme()

  useEffect(() => {
    setMounted(true)
  }, [])

  if (!mounted) {
    return (
      <button
        className="p-2 rounded-lg bg-transparent border border-slate-700 dark:border-slate-800 text-slate-400 opacity-0"
        aria-label="Toggle theme"
      >
        <Sun className="h-4 w-4" />
      </button>
    )
  }

  const isDark = resolvedTheme === "dark"

  return (
    <button
      onClick={() => setTheme(isDark ? "light" : "dark")}
      className="p-2 rounded-lg bg-transparent hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 border border-slate-200 dark:border-slate-800 transition-colors duration-150"
      aria-label="Toggle theme"
    >
      {isDark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
    </button>
  )
}
