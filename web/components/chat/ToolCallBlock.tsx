'use client'

import React, { useState } from "react"
import { ChevronDown, ChevronRight, Wrench, Check, AlertCircle } from "lucide-react"

export interface ToolCallBlockProps {
  type: "tool_call" | "tool_result"
  tool: string
  payload?: Record<string, unknown>
}

export default function ToolCallBlock({
  type,
  tool,
  payload,
}: ToolCallBlockProps): React.JSX.Element {
  const [isOpen, setIsOpen] = useState(false)

  const isCall = type === "tool_call"
  const isSuccess = !isCall && payload?.success !== false

  // Determine indicator colors
  const indicatorColor = isCall
    ? "text-indigo-500"
    : isSuccess
    ? "text-green-500"
    : "text-red-500"

  // Get preview of output
  let preview = ""
  if (!isCall) {
    const rawOutput = payload?.output || payload?.error || ""
    preview = typeof rawOutput === "string" ? rawOutput : JSON.stringify(rawOutput)
  }

  return (
    <div className="w-full flex justify-start my-2">
      <div className="w-full max-w-[80%] bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg overflow-hidden transition-all duration-150">
        {/* Header Button */}
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="w-full px-4 py-2.5 flex items-center justify-between text-xs font-mono text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-900/50 transition-colors text-left"
        >
          <div className="flex items-center gap-2 min-w-0">
            {isCall ? (
              <Wrench className={`h-3.5 w-3.5 shrink-0 ${indicatorColor}`} />
            ) : isSuccess ? (
              <Check className={`h-3.5 w-3.5 shrink-0 ${indicatorColor}`} />
            ) : (
              <AlertCircle className={`h-3.5 w-3.5 shrink-0 ${indicatorColor}`} />
            )}
            <span className="truncate">
              {isCall ? `🔧 [${tool}]` : `${isSuccess ? "✅" : "❌"} [${tool}]`}
            </span>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            {!isOpen && !isCall && preview && (
              <span className="text-[10px] max-w-[200px] truncate text-slate-400 dark:text-slate-500 font-sans">
                {preview.slice(0, 50)}
              </span>
            )}
            {isOpen ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
          </div>
        </button>

        {/* Details Content */}
        {isOpen && (
          <div className="border-t border-slate-200 dark:border-slate-800 p-3 bg-slate-100/50 dark:bg-slate-950 text-slate-800 dark:text-slate-300 text-xs font-mono whitespace-pre-wrap overflow-x-auto leading-relaxed max-h-[300px] overflow-y-auto">
            {isCall ? (
              <pre className="text-slate-700 dark:text-slate-300 font-mono">
                {JSON.stringify(payload || {}, null, 2)}
              </pre>
            ) : (
              <div className="text-slate-700 dark:text-slate-300 whitespace-pre-wrap break-all font-mono">
                {preview || "No output"}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
