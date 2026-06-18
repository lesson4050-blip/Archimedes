import { getOrCreateToken } from "./auth"

export interface MemoryEntry {
  id: string
  content: string
  role: "user" | "assistant"
  session_id: string
  timestamp: string
}

export async function fetchMemories(): Promise<MemoryEntry[]> {
  const token = await getOrCreateToken()
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

  const res = await fetch(`${baseUrl}/memory`, {
    method: "GET",
    headers: {
      "Authorization": `Bearer ${token}`,
      "Content-Type": "application/json",
    },
  })

  if (!res.ok) {
    throw new Error(`Failed to fetch memories: ${res.statusText}`)
  }

  const data = (await res.json()) as { memories: MemoryEntry[] }
  return data.memories
}

export async function deleteMemoryEntry(id: string): Promise<void> {
  const token = await getOrCreateToken()
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

  const res = await fetch(`${baseUrl}/memory/${id}`, {
    method: "DELETE",
    headers: {
      "Authorization": `Bearer ${token}`,
      "Content-Type": "application/json",
    },
  })

  if (!res.ok) {
    throw new Error(`Failed to delete memory: ${res.statusText}`)
  }
}
