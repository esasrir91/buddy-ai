import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Employee, EmployeeProfile } from '../types/pulse'

interface PulseStore {
  employeeId: string | null
  employee: Employee | null
  isOnboarded: boolean
  lastKnownProfile: EmployeeProfile | null  // survives clearEmployee()
  setEmployee: (id: string, data: Employee) => void
  clearEmployee: () => void
}

export const usePulseStore = create<PulseStore>()(
  persist(
    (set) => ({
      employeeId: null,
      employee: null,
      isOnboarded: false,
      lastKnownProfile: null,
      setEmployee: (id, data) =>
        set({
          employeeId: id,
          employee: data,
          isOnboarded: true,
          lastKnownProfile: data.profile,   // keep a copy that survives reset
        }),
      clearEmployee: () =>
        set({ employeeId: null, employee: null, isOnboarded: false }),
        // lastKnownProfile intentionally NOT cleared
    }),
    { name: 'pulse-store' },
  ),
)
