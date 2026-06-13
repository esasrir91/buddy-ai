import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { usePulseStore } from './hooks/usePulseStore'
import { getEmployee, createEmployee } from './api/pulse'
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

/** On every app load, validates the stored employee against the live server.
 *  If the server has restarted and lost state, it silently re-registers the
 *  employee from the profile already in localStorage — the user never sees
 *  the onboarding wizard again after their first setup. */
function EmployeeValidator() {
  const { employeeId, employee, setEmployee, clearEmployee } = usePulseStore()

  useEffect(() => {
    if (!employeeId) return

    getEmployee(employeeId).catch(async () => {
      // Server doesn't know this employee (e.g. restarted).
      // Try to silently re-register using the profile we already have in state.
      if (employee?.profile) {
        try {
          const result = await createEmployee({
            full_name:    employee.profile.full_name,
            role:         employee.profile.role,
            department:   employee.profile.department,
            skills:       employee.profile.skills,
            timezone:     employee.profile.timezone,
            reporting_to: employee.profile.reporting_to ?? undefined,
            company_name: employee.profile.company_name ?? undefined,
            bio:          employee.profile.bio ?? undefined,
          })
          // Update store with the new server-assigned ID
          setEmployee(result.employee_id, { ...employee, profile: result.profile })
        } catch {
          // Re-registration also failed — server might be down, don't clear state yet
          // so the user sees a meaningful error in the UI rather than a blank onboarding form
        }
      } else {
        // No profile data at all — must go through onboarding
        clearEmployee()
      }
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
