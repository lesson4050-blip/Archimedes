'use client'

import { useState, useEffect, useRef } from "react"
import { useParams, useSearchParams, useRouter } from "next/navigation"
import Sidebar from "@/components/layout/Sidebar"
import ChatInput from "@/components/chat/ChatInput"
import MessageList, { type MessageItem } from "@/components/chat/MessageList"
import { useWebSocket } from "@/lib/websocket"
import { useSessionStore } from "@/lib/store"
import { Wifi, WifiOff } from "lucide-react"

export default function ChatSessionClient(): React.JSX.Element {
  const params = useParams()
  const searchParams = useSearchParams()
  const router = useRouter()
  
  const sessionId = params.sessionId as string
  const initialMsg = searchParams.get("msg")

  const { messages: wsEvents, send, status } = useWebSocket(sessionId)
  const [localMessages, setLocalMessages] = useState<MessageItem[]>([])
  const [streamingContent, setStreamingContent] = useState("")
  const [inputValue, setInputValue] = useState("")
  
  const addSession = useSessionStore((state) => state.addSession)
  
  // Ref to track which WebSocket events we have already processed
  const processedEventsIndex = useRef(0)
  // Ref to track if we've sent the initial message from search parameter
  const sentInitial = useRef(false)

  // 1. Load history from localStorage on session change
  useEffect(() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem(`archimedes_history_${sessionId}`)
      if (saved) {
        try {
          setLocalMessages(JSON.parse(saved) as MessageItem[])
        } catch (e) {
          console.error("Failed to parse history", e)
        }
      } else {
        setLocalMessages([])
      }
    }
    setStreamingContent("")
    processedEventsIndex.current = 0
    sentInitial.current = false
  }, [sessionId])

  // 2. Persist history to localStorage on update
  useEffect(() => {
    if (typeof window !== "undefined" && localMessages.length > 0) {
      localStorage.setItem(`archimedes_history_${sessionId}`, JSON.stringify(localMessages))
    }
  }, [localMessages, sessionId])

  // 3. Process new WebSocket events as they arrive
  useEffect(() => {
    if (wsEvents.length <= processedEventsIndex.current) return

    for (let i = processedEventsIndex.current; i < wsEvents.length; i++) {
      const event = wsEvents[i]
      
      if (event.type === "stream") {
        const delta = (event.payload.delta as string) || ""
        setStreamingContent((prev) => prev + delta)
      } else if (event.type === "done") {
        setStreamingContent((currentStreaming) => {
          if (currentStreaming) {
            setLocalMessages((prev) => [
              ...prev,
              { role: "assistant", content: currentStreaming },
            ])
          }
          return ""
        })
      } else if (event.type === "error") {
        const errorMsg = (event.payload.message as string) || "Unknown error occurred"
        setLocalMessages((prev) => [
          ...prev,
          { role: "assistant", content: `Error: ${errorMsg}` },
        ])
        setStreamingContent("")
      }
    }

    processedEventsIndex.current = wsEvents.length
  }, [wsEvents])

  // 4. Send initial message if present and WebSocket is open
  useEffect(() => {
    if (status === "open" && initialMsg && !sentInitial.current) {
      sentInitial.current = true
      
      // Add user message to history
      setLocalMessages((prev) => [...prev, { role: "user", content: initialMsg }])
      
      // Make sure the session is registered in sidebar store
      addSession(sessionId, initialMsg.slice(0, 30) || "Chat Session")
      
      // Send via WS
      send(initialMsg)
      
      // Clear URL parameter cleanly
      const url = new URL(window.location.href)
      url.searchParams.delete("msg")
      router.replace(url.pathname, { scroll: false })
    }
  }, [status, initialMsg, sessionId, send, addSession, router])

  const handleSend = (text: string): void => {
    if (!text.trim() || status !== "open") return

    // Add user message to local state
    const newMsg: MessageItem = { role: "user", content: text }
    setLocalMessages((prev) => [...prev, newMsg])

    // Update session title if it was named "New Chat"
    const sessions = useSessionStore.getState().sessions
    const currentSession = sessions.find((s) => s.id === sessionId)
    if (currentSession?.title === "New Chat") {
      addSession(sessionId, text.slice(0, 30) || "Chat Session")
    }

    // Send to WS
    send(text)
  }

  return (
    <div className="flex h-screen w-screen bg-slate-50 dark:bg-slate-900 overflow-hidden text-slate-950 dark:text-slate-50">
      <Sidebar />

      <main className="flex-1 flex flex-col min-w-0 bg-white dark:bg-slate-900">
        {/* Top Header */}
        <header className="h-16 px-6 flex items-center justify-between border-b border-gray-200 dark:border-slate-800">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-sm">Active Chat Session</span>
          </div>
          
          {/* Status Indicator */}
          <div className="flex items-center gap-1.5">
            {status === "open" ? (
              <span className="flex items-center gap-1 text-xs font-medium text-green-500 bg-green-500/10 border border-green-500/20 px-2 py-0.5 rounded-full">
                <Wifi className="h-3 w-3" />
                Connected
              </span>
            ) : status === "connecting" ? (
              <span className="flex items-center gap-1 text-xs font-medium text-amber-500 bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 rounded-full animate-pulse">
                Connecting...
              </span>
            ) : (
              <span className="flex items-center gap-1 text-xs font-medium text-red-500 bg-red-500/10 border border-red-500/20 px-2 py-0.5 rounded-full">
                <WifiOff className="h-3 w-3" />
                Disconnected
              </span>
            )}
          </div>
        </header>

        {/* Message Area */}
        <MessageList messages={localMessages} streamingContent={streamingContent} />

        {/* Bottom Input */}
        <div className="p-4 border-t border-gray-200 dark:border-slate-800 bg-white dark:bg-slate-900">
          <div className="max-w-[720px] mx-auto">
            <ChatInput
              value={inputValue}
              onChange={setInputValue}
              onSend={handleSend}
              disabled={status !== "open"}
              placeholder={status === "open" ? "Message Archimedes..." : "Connecting to backend..."}
            />
          </div>
        </div>
      </main>
    </div>
  )
}
