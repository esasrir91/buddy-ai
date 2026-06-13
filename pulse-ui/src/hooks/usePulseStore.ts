import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Employee } from '../types/pulse'

interface PulseStore {
  employeeId: string | null
  employee: Employee | null
  isOnboarded: boolean
  setEmployee: (id: string, data: Employee) => void
  clearEmployee: () => void
}

export const usePulseStore = create<PulseStore>()(
  persist(
    (set) => ({
      employeeId: null,
      employee: null,
      isOnboarded: false,
      setEmployee: (id, data) =>
        set({ employeeId: id, employee: data, isOnboarded: true }),
      clearEmployee: () =>
        set({ employeeId: null, employee: null, isOnboarded: false }),
    }),
    { name: 'pulse-store' },
  ),
)
