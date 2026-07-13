'use client'

import React, { useEffect, useRef } from "react"
import MessageBubble from "./MessageBubble"
import StreamingBubble from "./StreamingBubble"
import ToolCallBlock from "./ToolCallBlock"

export interface MessageItem {
  role?: "user" | "assistant"
  content?: string
  type?: "message" | "tool_call" | "tool_result"
  tool?: string
  payload?: Record<string, unknown>
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
      {messages.map((msg, index) => {
        if (msg.type === "tool_call" || msg.type === "tool_result") {
          return (
            <ToolCallBlock
              key={index}
              type={msg.type}
              tool={msg.tool || ""}
              payload={msg.payload}
            />
          )
        }
        return (
          <MessageBubble
            key={index}
            role={msg.role || "assistant"}
            content={msg.content || ""}
          />
        )
      })}
      {streamingContent !== undefined && streamingContent !== "" && (
        <StreamingBubble content={streamingContent} isStreaming={true} />
      )}
      <div ref={bottomRef} />
    </div>
  )
}

