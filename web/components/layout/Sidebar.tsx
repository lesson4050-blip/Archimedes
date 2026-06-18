'use client'

import { useEffect } from "react"
import Link from "next/link"
import { usePathname, useRouter } from "next/navigation"
import { useSessionStore } from "@/lib/store"
import ThemeToggle from "@/components/ui/ThemeToggle"
import { MessageSquare, Plus, Brain } from "lucide-react"


export default function Sidebar(): React.JSX.Element {
  const router = useRouter()
  const pathname = usePathname()
  const { sessions, loadSessions } = useSessionStore()

  useEffect(() => {
    loadSessions()
  }, [loadSessions])

  const activeSessionId = pathname.startsWith("/chat/")
    ? pathname.split("/chat/")[1]
    : null

  const handleNewChat = (): void => {
    const newId = crypto.randomUUID()
    router.push(`/chat/${newId}`)
  }

  return (
    <aside className="w-[240px] flex-shrink-0 flex flex-col h-full bg-white dark:bg-slate-900 border-r border-gray-200 dark:border-slate-800 select-none">
      {/* Top Header */}
      <div className="h-16 px-4 flex items-center justify-between border-b border-gray-200 dark:border-slate-800">
        <Link href="/chat" className="flex items-center gap-2">
          <span className="text-lg font-bold bg-gradient-to-r from-indigo-500 to-purple-500 bg-clip-text text-transparent">
            Archimedes
          </span>
        </Link>
        <ThemeToggle />
      </div>

      {/* Action Area */}
      <div className="p-4">
        <button
          onClick={handleNewChat}
          className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-indigo-500 hover:bg-indigo-600 text-white font-medium text-sm rounded-lg transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:ring-offset-white dark:focus:ring-offset-slate-900"
        >
          <Plus className="h-4 w-4" />
          <span>New chat</span>
        </button>
      </div>

      {/* Sessions List */}
      <div className="flex-1 overflow-y-auto px-2 py-2 space-y-1 custom-scrollbar">
        {sessions.length === 0 ? (
          <div className="text-xs text-center text-slate-400 dark:text-slate-500 py-8">
            No chats yet
          </div>
        ) : (
          sessions.map((session) => {
            const isActive = activeSessionId === session.id
            return (
              <Link
                key={session.id}
                href={`/chat/${session.id}`}
                className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors duration-150 group ${
                  isActive
                    ? "bg-indigo-50 dark:bg-indigo-950 text-indigo-600 dark:text-indigo-400 font-medium"
                    : "text-slate-600 dark:text-slate-400 hover:bg-gray-100 dark:hover:bg-slate-800 hover:text-slate-900 dark:hover:text-slate-200"
                }`}
              >
                <MessageSquare className="h-4 w-4 flex-shrink-0" />
                <span className="truncate flex-1">{session.title}</span>
              </Link>
            )
          })
        )}
      </div>

      {/* Bottom Area (Memory Link) */}
      <div className="p-4 border-t border-gray-200 dark:border-slate-800">
        <Link
          href="/memory"
          className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors duration-150 ${
            pathname === "/memory"
              ? "bg-indigo-50 dark:bg-indigo-950 text-indigo-600 dark:text-indigo-400 font-medium"
              : "text-slate-600 dark:text-slate-400 hover:bg-gray-100 dark:hover:bg-slate-800 hover:text-slate-900 dark:hover:text-slate-200"
          }`}
        >
          <Brain className="h-5 w-5 flex-shrink-0" />
          <span>Memory</span>
        </Link>
      </div>
    </aside>
  )
}
