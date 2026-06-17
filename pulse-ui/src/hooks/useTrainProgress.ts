import { useCallback, useEffect, useRef, useState } from 'react'
import { createJobWebSocket, getTrainingJob } from '../api/train'
import type { JobEvent, JobStatus, StreamFrame } from '../types/train'

export function useTrainProgress(jobId: string | null) {
  const wsRef = useRef<WebSocket | null>(null)
  const [status, setStatus] = useState<JobStatus>('pending')
  const [progress, setProgress] = useState(0)
  const [phase, setPhase] = useState('')
  const [message, setMessage] = useState('')
  const [events, setEvents] = useState<JobEvent[]>([])
  const [done, setDone] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [connected, setConnected] = useState(false)

  const applyFrame = useCallback((frame: StreamFrame) => {
    if (frame.error) setError(frame.error)
    if (frame.event) {
      setEvents((prev) => [...prev, frame.event!])
      setProgress(frame.event.progress)
      setPhase(frame.event.phase)
      setMessage(frame.event.message)
    }
    if (frame.status) setStatus(frame.status)
    if (frame.progress !== undefined) setProgress(frame.progress)
    if (frame.phase) setPhase(frame.phase)
    if (frame.message) setMessage(frame.message)
    if (frame.done) setDone(true)
  }, [])

  useEffect(() => {
    if (!jobId) return

    let cancelled = false
    const poll = setInterval(async () => {
      if (done || cancelled) return
      try {
        const job = await getTrainingJob(jobId)
        if (cancelled) return
        setStatus(job.status)
        setProgress(job.progress)
        setPhase(job.phase)
        setMessage(job.message)
        if (['completed', 'failed', 'cancelled'].includes(job.status)) {
          setDone(true)
          if (job.error) setError(job.error)
        }
      } catch {
        /* ignore poll errors */
      }
    }, 3000)

    const ws = createJobWebSocket(jobId)
    wsRef.current = ws

    ws.onopen = () => setConnected(true)
    ws.onclose = () => setConnected(false)
    ws.onerror = () => setConnected(false)
    ws.onmessage = (ev) => {
      try {
        applyFrame(JSON.parse(ev.data) as StreamFrame)
      } catch {
        /* ignore */
      }
    }

    return () => {
      cancelled = true
      clearInterval(poll)
      ws.close()
      wsRef.current = null
    }
  }, [jobId, done, applyFrame])

  return { status, progress, phase, message, events, done, error, connected }
}
