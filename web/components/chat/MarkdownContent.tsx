'use client'

import React, { memo } from "react"
import ReactMarkdown from "react-markdown"
import type { Components } from "react-markdown"

const markdownComponents: Components = {
  strong: ({ node, ...props }) => <strong className="font-bold" {...props} />,
  code: ({ node, ...props }) => (
    <code className="bg-slate-200 dark:bg-slate-950 text-slate-900 dark:text-slate-200 px-1.5 py-0.5 rounded font-mono text-sm" {...props} />
  ),
  pre: ({ node, ...props }) => (
    <pre className="bg-slate-900 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg p-4 overflow-x-auto text-sm font-mono text-slate-800 dark:text-slate-200 leading-relaxed" {...props} />
  ),
  ul: ({ node, ...props }) => <ul className="list-disc pl-5 space-y-1" {...props} />,
  ol: ({ node, ...props }) => <ol className="list-decimal pl-5 space-y-1" {...props} />,
  li: ({ node, ...props }) => <li className="text-sm" {...props} />,
  p: ({ node, ...props }) => <p className="mb-2 last:mb-0" {...props} />,
}

interface MarkdownContentProps {
  content: string
}

export const MarkdownContent = memo(function MarkdownContent({ content }: MarkdownContentProps): React.JSX.Element {
  return <ReactMarkdown components={markdownComponents}>{content}</ReactMarkdown>
})
