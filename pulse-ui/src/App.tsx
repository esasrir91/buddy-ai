import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { usePulseStore } from './hooks/usePulseStore'
import { getEmployee } from './api/pulse'
import { Layout } from './components/layout/Layout'
import OnboardingWizard from './pages/OnboardingWizard'
import Dashboard from './pages/Dashboard'
import KTCenter from './pages/KTCenter'
import LiveKTSession from './pages/LiveKTSession'
import MeetingRoom from './pages/MeetingRoom'
import TaskBoard from './pages/TaskBoard'
import Chat from './pages/Chat'
import KnowledgeExplorer from './pages/KnowledgeExplorer'
import Settings from './pages/Settings'

function RequireEmployee({ children }: { children: React.ReactNode }) {
  const isOnboarded = usePulseStore((s) => s.isOnboarded)
  if (!isOnboarded) return <Navigate to="/" replace />
  return <>{children}</>
}

/** Validates the persisted employee against the live server on every app load.
 *  If the server no longer knows about it (after a restart), clear local state
 *  so the user is redirected back to onboarding instead of getting stuck. */
function EmployeeValidator() {
  const { employeeId, clearEmployee } = usePulseStore()

  useEffect(() => {
    if (!employeeId) return
    getEmployee(employeeId).catch(() => {
      // 404 or network error → server lost state, reset so onboarding runs again
      clearEmployee()
    })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return null
}

export default function App() {
  const isOnboarded = usePulseStore((s) => s.isOnboarded)

  return (
    <BrowserRouter>
      <EmployeeValidator />
      <Routes>
        {/* Onboarding wizard — redirect if already onboarded */}
        <Route
          path="/"
          element={isOnboarded ? <Navigate to="/dashboard" replace /> : <OnboardingWizard />}
        />

        {/* Protected app routes */}
        <Route
          element={
            <RequireEmployee>
              <Layout />
            </RequireEmployee>
          }
        >
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/kt" element={<KTCenter />} />
          <Route path="/kt/live/:sessionId" element={<LiveKTSession />} />
          <Route path="/meetings" element={<MeetingRoom />} />
          <Route path="/tasks" element={<TaskBoard />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/knowledge" element={<KnowledgeExplorer />} />
          <Route path="/settings" element={<Settings />} />
        </Route>

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
