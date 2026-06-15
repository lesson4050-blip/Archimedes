'use client'

import { useEffect, useRef } from "react"
import MessageBubble from "./MessageBubble"
import StreamingBubble from "./StreamingBubble"

export interface MessageItem {
  role: "user" | "assistant"
  content: string
}

export interface MessageListProps {
  messages: MessageItem[]
  streamingContent?: string
}

export default function MessageList({
  messages,
  streamingContent,
}: MessageListProps): React.JSX.Element {
  const bottomRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, streamingContent])

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
      {messages.map((msg, index) => (
        <MessageBubble
          key={index}
          role={msg.role}
          content={msg.content}
        />
      ))}
      {streamingContent !== undefined && streamingContent !== "" && (
        <StreamingBubble content={streamingContent} isStreaming={true} />
      )}
      <div ref={bottomRef} />
    </div>
  )
}
