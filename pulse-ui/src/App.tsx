import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { usePulseStore } from './hooks/usePulseStore'
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

export default function App() {
  const isOnboarded = usePulseStore((s) => s.isOnboarded)

  return (
    <BrowserRouter>
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
