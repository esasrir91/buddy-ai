import { useRef, useCallback, useState } from 'react'
import { createChatWebSocket } from '../api/pulse'

interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  streaming?: boolean
}

export function usePulseChat(employeeId: string) {
  const wsRef = useRef<WebSocket | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const [isStreaming, setIsStreaming] = useState(false)

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return
    const ws = createChatWebSocket(employeeId)
    ws.onopen = () => setIsConnected(true)
    ws.onclose = () => { setIsConnected(false); setIsStreaming(false) }
    ws.onerror = () => setIsConnected(false)
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data) as { chunk: string; done: boolean }
      if (data.done) {
        setIsStreaming(false)
        setMessages((prev) =>
          prev.map((m) => m.streaming ? { ...m, streaming: false } : m),
        )
        return
      }
      setMessages((prev) => {
        const last = prev[prev.length - 1]
        if (last?.streaming) {
          return [...prev.slice(0, -1), { ...last, content: last.content + data.chunk }]
        }
        return [...prev, { id: crypto.randomUUID(), role: 'assistant', content: data.chunk, streaming: true }]
      })
    }
    wsRef.current = ws
  }, [employeeId])

  const sendMessage = useCallback((text: string) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      connect()
      setTimeout(() => sendMessage(text), 300)
      return
    }
    setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: 'user', content: text }])
    setIsStreaming(true)
    wsRef.current.send(JSON.stringify({ message: text }))
  }, [connect])

  const disconnect = useCallback(() => {
    wsRef.current?.close()
    wsRef.current = null
  }, [])

  return { messages, isConnected, isStreaming, connect, sendMessage, disconnect }
}
