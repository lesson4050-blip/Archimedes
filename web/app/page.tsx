'use client'

import { useEffect } from "react"
import { useRouter } from "next/navigation"

export default function Home(): React.JSX.Element {
  const router = useRouter()

  useEffect(() => {
    router.replace("/chat")
  }, [router])

  return (
    <div className="flex h-screen w-screen items-center justify-center bg-white dark:bg-slate-900">
      <div className="animate-pulse text-indigo-500 font-medium text-sm">
        Loading...
      </div>
    </div>
  )
}
