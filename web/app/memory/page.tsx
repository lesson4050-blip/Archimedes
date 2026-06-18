'use client'

import { useEffect, useState } from "react"
import Sidebar from "@/components/layout/Sidebar"
import { fetchMemories, deleteMemoryEntry, type MemoryEntry } from "@/lib/api"
import { Trash2, Brain, Loader2 } from "lucide-react"

export default function MemoryPage(): React.JSX.Element {
  const [memories, setMemories] = useState<MemoryEntry[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const [expandedIds, setExpandedIds] = useState<Record<string, boolean>>({})

  useEffect(() => {
    async function loadData(): Promise<void> {
      try {
        setLoading(true)
        setError(null)
        const data = await fetchMemories()
        setMemories(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load memories")
      } finally {
        setLoading(false)
      }
    }
    void loadData()
  }, [])

  const handleDelete = async (id: string): Promise<void> => {
    if (!window.confirm("Delete this memory?")) return

    try {
      await deleteMemoryEntry(id)
      setMemories((prev) => prev.filter((m) => m.id !== id))
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to delete memory")
    }
  }

  const toggleExpand = (id: string): void => {
    setExpandedIds((prev) => ({
      ...prev,
      [id]: !prev[id],
    }))
  }

  function getRelativeTimeString(isoString: string): string {
    if (!isoString) return ""
    const date = new Date(isoString)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffSecs = Math.floor(diffMs / 1000)
    const diffMins = Math.floor(diffSecs / 60)
    const diffHours = Math.floor(diffMins / 60)
    const diffDays = Math.floor(diffHours / 24)

    if (diffSecs < 60) {
      return "just now"
    } else if (diffMins < 60) {
      return `${diffMins} minute${diffMins === 1 ? "" : "s"} ago`
    } else if (diffHours < 24) {
      return `${diffHours} hour${diffHours === 1 ? "" : "s"} ago`
    } else if (diffDays < 7) {
      return `${diffDays} day${diffDays === 1 ? "" : "s"} ago`
    } else {
      return date.toLocaleDateString()
    }
  }

  return (
    <div className="flex h-screen w-screen bg-slate-50 dark:bg-slate-900 overflow-hidden text-slate-950 dark:text-slate-50">
      <Sidebar />

      <main className="flex-1 flex flex-col h-full bg-slate-50 dark:bg-slate-900 overflow-hidden">
        {/* Header */}
        <header className="h-16 px-6 border-b border-gray-200 dark:border-slate-800 flex items-center justify-between bg-white dark:bg-slate-900 flex-shrink-0 select-none">
          <div className="flex items-center gap-2.5">
            <Brain className="h-5 w-5 text-indigo-500" />
            <h1 className="text-lg font-semibold text-slate-900 dark:text-slate-50">Memory</h1>
          </div>
        </header>

        {/* Content area */}
        <div className="flex-1 overflow-y-auto p-6 custom-scrollbar">
          <div className="max-w-[800px] mx-auto space-y-6">
            <div className="space-y-1 select-none">
              <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-50">Long-term Memory</h2>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                These are facts and contexts remembered across your conversation sessions.
              </p>
            </div>

            {loading ? (
              <div className="flex flex-col items-center justify-center py-20 space-y-3">
                <Loader2 className="h-8 w-8 text-indigo-500 animate-spin" />
                <span className="text-sm text-slate-500 dark:text-slate-400">Loading memories...</span>
              </div>
            ) : error ? (
              <div className="bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400 rounded-xl p-4 text-sm font-medium">
                {error}
              </div>
            ) : memories.length === 0 ? (
              <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-12 text-center select-none">
                <Brain className="h-12 w-12 text-slate-300 dark:text-slate-600 mx-auto mb-3" />
                <p className="text-slate-600 dark:text-slate-400 text-sm font-medium">No memories yet</p>
                <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">
                  Memory entries will appear here as you chat with Archimedes.
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {memories.map((entry) => {
                  const isTruncated = entry.content.length > 200
                  const isExpanded = !!expandedIds[entry.id]
                  const displayText = isTruncated && !isExpanded
                    ? `${entry.content.slice(0, 200)}...`
                    : entry.content

                  const badgeClass = entry.role === "user"
                    ? "bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border-indigo-500/20"
                    : "bg-green-500/10 text-green-600 dark:text-green-400 border-green-500/20"

                  return (
                    <div
                      key={entry.id}
                      className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-5 hover:border-indigo-500/30 transition-colors duration-200 flex flex-col md:flex-row md:items-start justify-between gap-4"
                    >
                      <div className="space-y-2.5 flex-1 min-w-0">
                        <div className="flex items-center gap-2 select-none">
                          <span className={`px-2 py-0.5 text-xs font-semibold rounded-full border ${badgeClass}`}>
                            {entry.role}
                          </span>
                          <span className="text-xs text-slate-400 dark:text-slate-500">
                            {getRelativeTimeString(entry.timestamp)}
                          </span>
                        </div>

                        <div
                          onClick={(): void => {
                            if (isTruncated) toggleExpand(entry.id)
                          }}
                          className={`text-sm text-slate-800 dark:text-slate-200 whitespace-pre-wrap leading-relaxed ${
                            isTruncated ? "cursor-pointer hover:text-indigo-500 dark:hover:text-indigo-400" : ""
                          }`}
                        >
                          {displayText}
                        </div>
                      </div>

                      <div className="flex-shrink-0 flex items-center md:self-start select-none">
                        <button
                          onClick={(): Promise<void> => handleDelete(entry.id)}
                          className="px-3 py-1.5 bg-red-500/10 hover:bg-red-500/20 text-red-600 dark:text-red-400 font-medium text-xs border border-red-500/20 rounded-lg transition-all duration-150 flex items-center gap-1.5"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                          <span>Delete</span>
                        </button>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}
