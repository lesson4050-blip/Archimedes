export async function getOrCreateToken(): Promise<string> {
  if (typeof window === "undefined") return ""

  const existing = localStorage.getItem("archimedes_token")
  if (existing) {
    try {
      const parts = existing.split(".")
      if (parts.length === 3) {
        const payload = JSON.parse(atob(parts[1]))
        if (payload.exp && payload.exp * 1000 > Date.now()) {
          return existing
        }
      }
    } catch {
      // If decoding fails, fall through to fetch a new token
    }
  }

  try {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
    const res = await fetch(`${apiUrl}/auth/token`, { method: "POST" })
    if (!res.ok) return ""
    const data = (await res.json()) as { access_token: string }
    localStorage.setItem("archimedes_token", data.access_token)
    return data.access_token
  } catch {
    return ""
  }
}
