import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { usePulseStore } from './hooks/usePulseStore'
import { getEmployee, createEmployee } from './api/pulse'
import type { EmployeeProfile, Employee } from './types/pulse'
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
import Workspace from './pages/Workspace'
import Memory from './pages/Memory'

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
  const { employeeId, employee, lastKnownProfile, setEmployee, clearEmployee } = usePulseStore()

  useEffect(() => {
    // Helper: register from a profile object
    const reRegister = async (profile: EmployeeProfile) => {
      try {
        const result = await createEmployee({
          full_name:    profile.full_name,
          role:         profile.role,
          department:   profile.department,
          skills:       profile.skills,
          timezone:     profile.timezone,
          reporting_to: profile.reporting_to ?? undefined,
          company_name: profile.company_name ?? undefined,
          bio:          profile.bio ?? undefined,
        })
        const emp: Employee = {
          employee_id:    result.employee_id,
          profile:        result.profile,
          memory_summary: { kt_sessions_completed: 0, kt_domains: [], colleagues_known: 0, decisions_logged: 0, projects_tracked: [] },
          task_summary:   {},
          kt_domains:     [],
        }
        setEmployee(result.employee_id, emp)
      } catch {
        // Server down or config missing — don't clear, just wait
      }
    }

    if (employeeId) {
      // Employee ID exists — verify it's still alive on the server
      getEmployee(employeeId).catch(async () => {
        const profile = employee?.profile ?? lastKnownProfile
        if (profile) {
          await reRegister(profile)
        } else {
          clearEmployee()
        }
      })
    } else if (lastKnownProfile) {
      // ID was cleared (e.g. by old code) but we still have profile data — re-register silently
      reRegister(lastKnownProfile)
    }
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
          <Route path="/workspace" element={<Workspace />} />
          <Route path="/memory" element={<Memory />} />
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
