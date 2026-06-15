'use client'

import { useState, useRef } from "react"
import { useRouter } from "next/navigation"
import Sidebar from "@/components/layout/Sidebar"
import ChatInput, { type ChatInputRef } from "@/components/chat/ChatInput"
import { useSessionStore } from "@/lib/store"
import { Plus, Terminal, HelpCircle } from "lucide-react"

export default function ChatHome(): React.JSX.Element {
  const router = useRouter()
  const [inputValue, setInputValue] = useState("")
  const chatInputRef = useRef<ChatInputRef | null>(null)
  const addSession = useSessionStore((state) => state.addSession)

  const handleSend = (message: string): void => {
    if (!message.trim()) return
    const sessionId = crypto.randomUUID()
    addSession(sessionId, message.slice(0, 30) || "New Chat")
    router.push(`/chat/${sessionId}?msg=${encodeURIComponent(message.trim())}`)
  }

  const handleNewChat = (): void => {
    const newId = crypto.randomUUID()
    addSession(newId, "New Chat")
    router.push(`/chat/${newId}`)
  }

  const handleRunBash = (): void => {
    setInputValue("Run: ")
    setTimeout(() => {
      chatInputRef.current?.focus()
    }, 50)
  }

  const handleAskAnything = (): void => {
    chatInputRef.current?.focus()
  }

  return (
    <div className="flex h-screen w-screen bg-slate-50 dark:bg-slate-900 overflow-hidden text-slate-950 dark:text-slate-50">
      <Sidebar />
      
      <main className="flex-1 flex flex-col items-center justify-center px-4 md:px-8 relative bg-slate-50 dark:bg-slate-900">
        <div className="w-full max-w-[640px] flex flex-col items-center space-y-8">
          
          {/* Centered Headers */}
          <div className="text-center space-y-2 select-none">
            <h1 className="text-4xl font-extrabold tracking-tight bg-gradient-to-r from-indigo-500 via-purple-500 to-indigo-500 dark:from-indigo-400 dark:via-purple-400 dark:to-indigo-400 bg-clip-text text-transparent pb-1">
              What can I do for you?
            </h1>
            <p className="text-sm text-slate-500 dark:text-slate-400 font-medium">
              Archimedes — autonomous AI agent
            </p>
          </div>

          {/* Centered Input Box */}
          <div className="w-full">
            <ChatInput
              ref={chatInputRef}
              value={inputValue}
              onChange={setInputValue}
              onSend={handleSend}
              placeholder="Ask anything or run a command..."
            />
          </div>

          {/* Quick-Action Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 w-full">
            <button
              onClick={handleNewChat}
              className="flex flex-col items-start p-4 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl hover:border-indigo-500/50 dark:hover:border-indigo-500/30 transition-all duration-200 text-left group"
            >
              <div className="p-2 bg-indigo-50 dark:bg-indigo-955 text-indigo-500 rounded-lg mb-3">
                <Plus className="h-5 w-5" />
              </div>
              <h3 className="font-semibold text-sm text-slate-800 dark:text-slate-200 group-hover:text-indigo-500 dark:group-hover:text-indigo-400 transition-colors">
                New chat
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                Start a fresh session
              </p>
            </button>

            <button
              onClick={handleRunBash}
              className="flex flex-col items-start p-4 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl hover:border-indigo-500/50 dark:hover:border-indigo-500/30 transition-all duration-200 text-left group"
            >
              <div className="p-2 bg-indigo-50 dark:bg-indigo-955 text-indigo-500 rounded-lg mb-3">
                <Terminal className="h-5 w-5" />
              </div>
              <h3 className="font-semibold text-sm text-slate-800 dark:text-slate-200 group-hover:text-indigo-500 dark:group-hover:text-indigo-400 transition-colors">
                Run bash command
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                Pre-fill with Run: prefix
              </p>
            </button>

            <button
              onClick={handleAskAnything}
              className="flex flex-col items-start p-4 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl hover:border-indigo-500/50 dark:hover:border-indigo-500/30 transition-all duration-200 text-left group"
            >
              <div className="p-2 bg-indigo-50 dark:bg-indigo-955 text-indigo-500 rounded-lg mb-3">
                <HelpCircle className="h-5 w-5" />
              </div>
              <h3 className="font-semibold text-sm text-slate-800 dark:text-slate-200 group-hover:text-indigo-500 dark:group-hover:text-indigo-400 transition-colors">
                Ask anything
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                Focus input field
              </p>
            </button>
          </div>

        </div>
      </main>
    </div>
  )
}
