'use client'

import { MarkdownContent } from "./MarkdownContent"

export interface MessageBubbleProps {
  role: "user" | "assistant"
  content: string
}

export default function MessageBubble({ role, content }: MessageBubbleProps): React.JSX.Element {
  const isUser = role === "user"

  return (
    <div className={`flex w-full ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] px-4 py-3 text-sm leading-relaxed ${
          isUser
            ? "bg-indigo-600 text-white rounded-2xl rounded-tr-sm"
            : "bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-slate-100 rounded-2xl rounded-tl-sm"
        }`}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap">{content}</p>
        ) : (
          <MarkdownContent content={content} />
        )}
      </div>
    </div>
  )
}
