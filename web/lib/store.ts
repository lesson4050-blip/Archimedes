'use client'

import { create } from 'zustand'

export interface SessionItem {
  id: string
  title: string
  createdAt: string
}

interface SessionState {
  sessions: SessionItem[]
  addSession: (id: string, title?: string) => void
  loadSessions: () => void
}

export const useSessionStore = create<SessionState>((set) => ({
  sessions: [],
  addSession: (id: string, title = "New Chat") => {
    set((state) => {
      const exists = state.sessions.some((s) => s.id === id)
      if (exists) return state
      
      const newSession: SessionItem = {
        id,
        title,
        createdAt: new Date().toISOString(),
      }
      const updated = [newSession, ...state.sessions]
      if (typeof window !== 'undefined') {
        localStorage.setItem('archimedes_sessions', JSON.stringify(updated))
      }
      return { sessions: updated }
    })
  },
  loadSessions: () => {
    if (typeof window === 'undefined') return
    const stored = localStorage.getItem('archimedes_sessions')
    if (stored) {
      try {
        set({ sessions: JSON.parse(stored) as SessionItem[] })
      } catch (e) {
        console.error("Failed to parse sessions", e)
      }
    }
  },
}))
