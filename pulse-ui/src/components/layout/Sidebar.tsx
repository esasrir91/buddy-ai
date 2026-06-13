import { NavLink, useNavigate } from 'react-router-dom'
import { usePulseStore } from '../../hooks/usePulseStore'
import {
  LayoutDashboard, BookOpen, Video, CheckSquare,
  MessageSquare, Search, Settings, LogOut, Cpu,
} from 'lucide-react'
import clsx from 'clsx'

const navItems = [
  { to: '/dashboard',   icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/kt',          icon: BookOpen,         label: 'KT Center' },
  { to: '/meetings',    icon: Video,            label: 'Meetings' },
  { to: '/tasks',       icon: CheckSquare,      label: 'Tasks' },
  { to: '/chat',        icon: MessageSquare,    label: 'Chat' },
  { to: '/knowledge',   icon: Search,           label: 'Knowledge' },
  { to: '/settings',    icon: Settings,         label: 'Settings' },
]

export function Sidebar() {
  const { employee, clearEmployee } = usePulseStore()
  const navigate = useNavigate()

  return (
    <aside className="w-60 flex-shrink-0 bg-slate-900 border-r border-slate-800 flex flex-col h-screen">
      {/* Logo */}
      <div className="px-4 py-5 border-b border-slate-800 flex items-center gap-3">
        <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center pulse-dot">
          <Cpu size={16} className="text-white" />
        </div>
        <div>
          <p className="text-sm font-bold text-white tracking-wide">PULSE</p>
          <p className="text-[10px] text-slate-500">Virtual Employee</p>
        </div>
      </div>

      {/* Employee card */}
      {employee && (
        <div className="mx-3 my-3 p-3 bg-slate-800 rounded-xl">
          <div className="flex items-center gap-2">
            <div className="w-9 h-9 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white font-bold text-sm flex-shrink-0">
              {employee.profile.full_name.charAt(0)}
            </div>
            <div className="min-w-0">
              <p className="text-sm font-semibold text-white truncate">{employee.profile.full_name}</p>
              <p className="text-[11px] text-slate-400 truncate">{employee.profile.role}</p>
            </div>
          </div>
          <div className="mt-2 flex items-center gap-1.5">
            <div className="w-1.5 h-1.5 rounded-full bg-green-400" />
            <span className="text-[10px] text-slate-400">Available</span>
          </div>
        </div>
      )}

      {/* Nav items */}
      <nav className="flex-1 px-2 py-2 space-y-0.5 overflow-y-auto">
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              clsx(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors',
                isActive
                  ? 'bg-blue-600/20 text-blue-400 font-medium'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800',
              )
            }
          >
            <Icon size={16} />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Logout */}
      <div className="px-2 pb-4">
        <button
          onClick={() => { clearEmployee(); navigate('/') }}
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-slate-400 hover:text-red-400 hover:bg-red-400/10 transition-colors"
        >
          <LogOut size={16} />
          Reset Employee
        </button>
      </div>
    </aside>
  )
}
