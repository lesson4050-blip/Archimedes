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

export function useWebSocket(sessionId: string): UseWebSocketReturn {
  const ws = useRef<WebSocket | null>(null)
  const [messages, setMessages] = useState<WSMessage[]>([])
  const [status, setStatus] = useState<WSStatus>("connecting")

  useEffect(() => {
    const token = typeof window !== "undefined" ? localStorage.getItem("archimedes_token") ?? "" : ""
    const wsUrl = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws"
    const url = `${wsUrl}/${sessionId}?token=${token}`

    ws.current = new WebSocket(url)
    ws.current.onopen = () => setStatus("open")
    ws.current.onclose = () => setStatus("closed")
    ws.current.onerror = () => setStatus("error")
    ws.current.onmessage = (e: MessageEvent) => {
      try {
        const msg = JSON.parse(e.data as string) as WSMessage
        setMessages((prev) => [...prev, msg])
      } catch (err) {
        console.error("Failed to parse WebSocket message:", err)
      }
    }

    return () => {
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
