export async function getOrCreateToken(): Promise<string> {
  if (typeof window === "undefined") return ""

  const existing = localStorage.getItem("archimedes_token")
  if (existing) return existing

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
