import { useRef, useCallback, useState, useEffect } from 'react'
import { createChatWebSocket } from '../api/pulse'

export interface ChatMessage {
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
  const pendingRef = useRef<string | null>(null)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const retryCount = useRef(0)
  const MAX_RETRIES = 5

  const connect = useCallback(() => {
    if (!employeeId) return
    if (wsRef.current?.readyState === WebSocket.OPEN) return
    if (wsRef.current?.readyState === WebSocket.CONNECTING) return

    const ws = createChatWebSocket(employeeId)

    ws.onopen = () => {
      setIsConnected(true)
      retryCount.current = 0
      // Flush any message that was queued before connection was ready
      if (pendingRef.current) {
        ws.send(JSON.stringify({ message: pendingRef.current }))
        pendingRef.current = null
      }
    }

    ws.onclose = () => {
      setIsConnected(false)
      setIsStreaming(false)
      wsRef.current = null
      // Auto-reconnect with backoff (only if we haven't hit max retries)
      if (retryCount.current < MAX_RETRIES) {
        retryCount.current += 1
        const delay = Math.min(1000 * retryCount.current, 5000)
        reconnectTimer.current = setTimeout(connect, delay)
      }
    }

    ws.onerror = () => {
      setIsConnected(false)
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as { chunk?: string; done?: boolean; error?: string }
        if (data.error) {
          // Server closed the connection with a fatal error (e.g. employee not found).
          // Stop all reconnect attempts so we don't flood the server.
          retryCount.current = MAX_RETRIES
          ws.close()
          return
        }
        if (data.done) {
          setIsStreaming(false)
          setMessages((prev) =>
            prev.map((m) => (m.streaming ? { ...m, streaming: false } : m)),
          )
          return
        }
        if (data.chunk) {
          setIsStreaming(true)
          setMessages((prev) => {
            const last = prev[prev.length - 1]
            if (last?.streaming) {
              return [...prev.slice(0, -1), { ...last, content: last.content + data.chunk }]
            }
            return [
              ...prev,
              { id: crypto.randomUUID(), role: 'assistant', content: data.chunk!, streaming: true },
            ]
          })
        }
      } catch {
        // ignore malformed frames
      }
    }

    wsRef.current = ws
  }, [employeeId])

  // Connect on mount, disconnect on unmount
  useEffect(() => {
    connect()
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
      retryCount.current = MAX_RETRIES // stop retrying on unmount
      wsRef.current?.close()
      wsRef.current = null
    }
  }, [connect])

  const sendMessage = useCallback(
    (text: string) => {
      // Optimistically add the user message
      setMessages((prev) => [
        ...prev,
        { id: crypto.randomUUID(), role: 'user', content: text },
      ])

      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ message: text }))
      } else {
        // Queue it — will be flushed in ws.onopen
        pendingRef.current = text
        connect()
      }
    },
    [connect],
  )

  const disconnect = useCallback(() => {
    if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
    retryCount.current = MAX_RETRIES
    wsRef.current?.close()
    wsRef.current = null
    setIsConnected(false)
  }, [])

  return { messages, isConnected, isStreaming, sendMessage, disconnect }
}
