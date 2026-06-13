import { useState, useCallback } from 'react'
import type { KTTurn, KTSessionState } from '../types/pulse'
import * as api from '../api/pulse'

export function useKTSession(employeeId: string) {
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [state, setState] = useState<KTSessionState | null>(null)
  const [turns, setTurns] = useState<KTTurn[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const startSession = useCallback(
    async (sessionName: string, knowledgeGiver: string, sourceType = 'human_chat') => {
      setIsLoading(true)
      setError(null)
      try {
        const res = await api.createLiveKTSession(employeeId, {
          session_name: sessionName,
          knowledge_giver: knowledgeGiver,
          source_type: sourceType,
        })
        setSessionId(res.session_id)
        setState(res.state)
        setTurns([])
      } catch (e) {
        setError(String(e))
      } finally {
        setIsLoading(false)
      }
    },
    [employeeId],
  )

  const explain = useCallback(
    async (text: string): Promise<KTTurn | null> => {
      if (!sessionId) return null
      setIsLoading(true)
      try {
        const turn = await api.humanExplains(employeeId, sessionId, text)
        setTurns((prev) => [...prev, turn])
        setState((prev) => prev ? { ...prev, confidence_score: turn.confidence_score, mental_model_draft: turn.mental_model_draft, phase: turn.phase } : prev)
        return turn
      } catch (e) {
        setError(String(e))
        return null
      } finally {
        setIsLoading(false)
      }
    },
    [employeeId, sessionId],
  )

  const answer = useCallback(
    async (answers: Record<string, string>): Promise<KTTurn | null> => {
      if (!sessionId) return null
      setIsLoading(true)
      try {
        const turn = await api.humanAnswers(employeeId, sessionId, answers)
        setTurns((prev) => [...prev, turn])
        setState((prev) => prev ? { ...prev, confidence_score: turn.confidence_score, mental_model_draft: turn.mental_model_draft, phase: turn.phase } : prev)
        return turn
      } catch (e) {
        setError(String(e))
        return null
      } finally {
        setIsLoading(false)
      }
    },
    [employeeId, sessionId],
  )

  const correct = useCallback(
    async (correction: string): Promise<KTTurn | null> => {
      if (!sessionId) return null
      setIsLoading(true)
      try {
        const turn = await api.humanCorrects(employeeId, sessionId, correction)
        setTurns((prev) => [...prev, turn])
        setState((prev) => prev ? { ...prev, confidence_score: turn.confidence_score, phase: turn.phase } : prev)
        return turn
      } catch (e) {
        setError(String(e))
        return null
      } finally {
        setIsLoading(false)
      }
    },
    [employeeId, sessionId],
  )

  const commit = useCallback(async () => {
    if (!sessionId) return null
    setIsLoading(true)
    try {
      const summary = await api.commitKTSession(employeeId, sessionId)
      return summary
    } catch (e) {
      setError(String(e))
      return null
    } finally {
      setIsLoading(false)
    }
  }, [employeeId, sessionId])

  return { sessionId, state, turns, isLoading, error, startSession, explain, answer, correct, commit }
}
