'use client'

import { motion } from "framer-motion"

export interface StreamingBubbleProps {
  content: string
  isStreaming?: boolean
}

export default function StreamingBubble({
  content,
  isStreaming = true,
}: StreamingBubbleProps): React.JSX.Element {
  return (
    <div className="flex w-full justify-start">
      <motion.div
        initial={{ opacity: 0, y: 4 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.15 }}
        className="motion-reduce:transition-none max-w-[80%] px-4 py-3 bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-slate-100 rounded-2xl rounded-tl-sm text-sm leading-relaxed"
      >
        <span className="whitespace-pre-wrap">{content}</span>
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
