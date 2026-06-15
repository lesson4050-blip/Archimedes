'use client'

import * as React from "react"
import { ThemeProvider as NextThemesProvider } from "next-themes"

declare module "next-themes" {
  export type ThemeProviderProps = React.ComponentProps<typeof NextThemesProvider>
}

import { type ThemeProviderProps } from "next-themes"

export function ThemeProvider({ children, ...props }: ThemeProviderProps): React.JSX.Element {
  return <NextThemesProvider {...props}>{children}</NextThemesProvider>
}
