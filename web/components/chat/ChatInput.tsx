'use client'

import { useRef, useImperativeHandle, forwardRef, useEffect } from "react"
import { Send } from "lucide-react"

export interface ChatInputProps {
  value: string
  onChange: (val: string) => void
  onSend?: (message: string) => void
  placeholder?: string
  disabled?: boolean
}

export interface ChatInputRef {
  focus: () => void
}

const ChatInput = forwardRef<ChatInputRef, ChatInputProps>(
  ({ value, onChange, onSend, placeholder = "Message Archimedes...", disabled = false }, ref) => {
    const textareaRef = useRef<HTMLTextAreaElement | null>(null)

    useImperativeHandle(ref, () => ({
      focus: () => {
        textareaRef.current?.focus()
      },
    }))

    // Auto-resize textarea height based on content
    useEffect(() => {
      const textarea = textareaRef.current
      if (!textarea) return

      textarea.style.height = "auto"
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`
    }, [value])

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>): void => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault()
        submitMessage()
      }
    }

    const submitMessage = (): void => {
      if (!value.trim() || disabled) return
      if (onSend) {
        onSend(value.trim())
        onChange("")
      }
    }

    return (
      <div className="relative flex items-end w-full bg-slate-900 border border-slate-700 focus-within:border-indigo-500 rounded-lg p-2 transition-colors duration-150">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled}
          rows={1}
          className="w-full pl-2 pr-12 py-1 bg-transparent text-slate-100 placeholder:text-slate-500 text-sm outline-none resize-none overflow-y-auto max-h-[200px] align-bottom"
        />

        {onSend && (
          <button
            onClick={submitMessage}
            disabled={disabled || !value.trim()}
            className="absolute right-3 bottom-2.5 p-1.5 bg-indigo-500 hover:bg-indigo-600 disabled:bg-slate-800 disabled:opacity-50 text-white rounded-md transition-all duration-150 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            aria-label="Send message"
          >
            <Send className="h-3.5 w-3.5" />
          </button>
        )}
      </div>
    )
  }
)

ChatInput.displayName = "ChatInput"

export default ChatInput
