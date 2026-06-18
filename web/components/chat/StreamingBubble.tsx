'use client'

import React, { useState, useEffect, useRef } from "react"
import { motion } from "framer-motion"
import { MarkdownContent } from "./MarkdownContent"

export interface StreamingBubbleProps {
  content: string
  isStreaming?: boolean
}

export default function StreamingBubble({
  content,
  isStreaming = true,
}: StreamingBubbleProps): React.JSX.Element {
  const [displayedContent, setDisplayedContent] = useState(content)
  const latestContentRef = useRef(content)
  const lastRenderTimeRef = useRef(0)
  const timerRef = useRef<NodeJS.Timeout | null>(null)

  // Sync latest content ref
  latestContentRef.current = content

  useEffect(() => {
    // If streaming ended, immediately force the final render
    if (!isStreaming) {
      if (timerRef.current) {
        clearTimeout(timerRef.current)
        timerRef.current = null
      }
      setDisplayedContent(content)
      lastRenderTimeRef.current = Date.now()
      return
    }

    const now = Date.now()
    const timeSinceLastRender = now - lastRenderTimeRef.current
    const throttleInterval = 90 // Throttle updates to ~90ms

    if (timeSinceLastRender >= throttleInterval) {
      // Enough time has elapsed since the last state update, render immediately
      if (timerRef.current) {
        clearTimeout(timerRef.current)
        timerRef.current = null
      }
      setDisplayedContent(content)
      lastRenderTimeRef.current = now
    } else {
      // If we already scheduled a future update, do nothing (it will pick up latestContentRef.current)
      // Otherwise, schedule an update to execute once the interval has passed.
      if (!timerRef.current) {
        const delay = throttleInterval - timeSinceLastRender
        timerRef.current = setTimeout(() => {
          setDisplayedContent(latestContentRef.current)
          lastRenderTimeRef.current = Date.now()
          timerRef.current = null
        }, delay)
      }
    }

    // Cleanup timers on change/unmount
    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current)
        timerRef.current = null
      }
    }
  }, [content, isStreaming])

  return (
    <div className="flex w-full justify-start">
      <motion.div
        initial={{ opacity: 0, y: 4 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.15 }}
        className="motion-reduce:transition-none max-w-[80%] px-4 py-3 bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-slate-100 rounded-2xl rounded-tl-sm text-sm leading-relaxed"
      >
        <MarkdownContent content={displayedContent} />
        {isStreaming && (
          <span
            className="inline-block w-1.5 h-4 ml-1 bg-indigo-500 dark:bg-indigo-400 align-middle animate-pulse"
            aria-hidden="true"
          />
        )}
      </motion.div>
    </div>
  )
}
