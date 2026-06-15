import { useEffect, useRef, useState, useCallback } from "react"

export type WSStatus = "connecting" | "open" | "closed" | "error"

export interface WSMessage {
  type: "stream" | "tool_call" | "tool_result" | "done" | "error"
  session_id: string
  payload: Record<string, unknown>
}

interface UseWebSocketReturn {
  messages: WSMessage[]
  send: (message: string) => void
  status: WSStatus
}

async function getOrCreateToken(): Promise<string> {
  if (typeof window === "undefined") return ""

  const existing = localStorage.getItem("archimedes_token")
  if (existing) return existing

  try {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
    const res = await fetch(`${apiUrl}/auth/token`, { method: "POST" })
    if (!res.ok) return ""
    const data = (await res.json()) as { access_token: string }
    localStorage.setItem("archimedes_token", data.access_token)
    return data.access_token
  } catch {
    return ""
  }
}

export function useWebSocket(sessionId: string): UseWebSocketReturn {
  const ws = useRef<WebSocket | null>(null)
  const [messages, setMessages] = useState<WSMessage[]>([])
  const [status, setStatus] = useState<WSStatus>("connecting")

  useEffect(() => {
    let cancelled = false

    async function connect(): Promise<void> {
      const token = await getOrCreateToken()
      if (cancelled) return

      const wsUrl = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws"
      const url = `${wsUrl}/${sessionId}?token=${token}`

      const socket = new WebSocket(url)
      ws.current = socket

      socket.onopen = () => {
        if (!cancelled) setStatus("open")
      }
      socket.onclose = () => {
        if (!cancelled) setStatus("closed")
      }
      socket.onerror = () => {
        if (!cancelled) setStatus("error")
      }
      socket.onmessage = (e: MessageEvent) => {
        try {
          const msg = JSON.parse(e.data as string) as WSMessage
          if (!cancelled) setMessages((prev) => [...prev, msg])
        } catch (err) {
          console.error("Failed to parse WebSocket message:", err)
        }
      }
    }

    void connect()

    return () => {
      cancelled = true
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
