import { NavLink, useNavigate } from 'react-router-dom'
import { useState, useEffect, useRef } from 'react'
import { usePulseStore } from '../../hooks/usePulseStore'
import {
  LayoutDashboard, BookOpen, Video, CheckSquare,
  MessageSquare, Search, Settings, LogOut, Cpu, Bell, X, FolderOpen, Brain, Flame,
} from 'lucide-react'
import { getNotifications, markAllNotificationsRead } from '../../api/pulse'
import type { PulseNotification } from '../../types/pulse'
import clsx from 'clsx'

const navItems = [
  { to: '/dashboard',   icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/kt',          icon: BookOpen,         label: 'KT Center' },
  { to: '/meetings',    icon: Video,            label: 'Meetings' },
  { to: '/tasks',       icon: CheckSquare,      label: 'Tasks' },
  { to: '/workspace',   icon: FolderOpen,       label: 'Workspace' },
  { to: '/memory',      icon: Brain,            label: 'Memory' },
  { to: '/chat',        icon: MessageSquare,    label: 'Chat' },
  { to: '/train',       icon: Flame,            label: 'Fire' },
  { to: '/knowledge',   icon: Search,           label: 'Knowledge' },
  { to: '/settings',    icon: Settings,         label: 'Settings' },
]

const NOTIF_COLORS: Record<string, string> = {
  success: 'border-l-green-500 bg-green-500/5',
  standup: 'border-l-amber-500 bg-amber-500/5',
  suggestion: 'border-l-cyan-500 bg-cyan-500/5',
  warning: 'border-l-red-500 bg-red-500/5',
  info: 'border-l-blue-500 bg-blue-500/5',
}

export function Sidebar() {
  const { employeeId, employee, clearEmployee } = usePulseStore()
  const navigate = useNavigate()
  const [notifications, setNotifications] = useState<PulseNotification[]>([])
  const [unread, setUnread] = useState(0)
  const [showNotifs, setShowNotifs] = useState(false)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const loadNotifs = async () => {
    if (!employeeId) return
    try {
      const r = await getNotifications(employeeId)
      setNotifications(r.notifications)
      setUnread(r.unread)
    } catch { /* ignore */ }
  }

  useEffect(() => {
    loadNotifs()
    pollRef.current = setInterval(loadNotifs, 15000)
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [employeeId])

  const handleMarkAllRead = async () => {
    if (!employeeId) return
    await markAllNotificationsRead(employeeId).catch(() => {})
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })))
    setUnread(0)
  }

  return (
    <aside className="w-60 flex-shrink-0 bg-slate-900 border-r border-slate-800 flex flex-col h-screen">
      {/* Logo */}
      <div className="px-4 py-5 border-b border-slate-800 flex items-center gap-3">
        <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center pulse-dot">
          <Cpu size={16} className="text-white" />
        </div>
        <div className="flex-1">
          <p className="text-sm font-bold text-white tracking-wide">PULSE</p>
          <p className="text-[10px] text-slate-500">Virtual Employee</p>
        </div>
        {/* Notifications bell */}
        <button
          onClick={() => { setShowNotifs(!showNotifs); if (!showNotifs) loadNotifs() }}
          className="relative p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition-colors"
          title="Notifications"
        >
          <Bell size={16} />
          {unread > 0 && (
            <span className="absolute -top-0.5 -right-0.5 w-4 h-4 bg-blue-500 rounded-full text-[9px] text-white flex items-center justify-center font-bold">
              {unread > 9 ? '9+' : unread}
            </span>
          )}
        </button>
      </div>

      {/* Notifications panel (inline) */}
      {showNotifs && (
        <div className="border-b border-slate-800 bg-slate-950">
          <div className="flex items-center justify-between px-3 py-2">
            <span className="text-xs font-semibold text-slate-300">Notifications</span>
            <div className="flex items-center gap-2">
              {unread > 0 && (
                <button onClick={handleMarkAllRead} className="text-[10px] text-slate-500 hover:text-slate-300">
                  Mark all read
                </button>
              )}
              <button onClick={() => setShowNotifs(false)} className="text-slate-600 hover:text-slate-300">
                <X size={13} />
              </button>
            </div>
          </div>
          <div className="max-h-72 overflow-y-auto">
            {notifications.length === 0 ? (
              <p className="text-xs text-slate-600 text-center py-4">No notifications yet</p>
            ) : (
              notifications.slice(0, 20).map((n) => (
                <div
                  key={n.id}
                  className={clsx(
                    'px-3 py-2 border-l-2 border-b border-slate-800/50 last:border-b-0',
                    NOTIF_COLORS[n.type] ?? 'border-l-slate-600',
                    n.read && 'opacity-50',
                  )}
                >
                  <p className="text-[11px] text-slate-300 leading-relaxed line-clamp-3">{n.message}</p>
                  <p className="text-[10px] text-slate-600 mt-0.5">
                    {new Date(n.ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </p>
                </div>
              ))
            )}
          </div>
        </div>
      )}

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
            <div className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
            <span className="text-[10px] text-slate-400">Autonomous mode</span>
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

      {/* Reset */}
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
