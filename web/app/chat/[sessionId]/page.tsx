import ChatSessionClient from "./ChatSessionClient"

export const dynamic = "force-static"
export async function generateStaticParams() {
  return [{ sessionId: "session-placeholder" }]
}

export default function ChatSession() {
  return <ChatSessionClient />
}
