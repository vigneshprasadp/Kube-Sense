import { NavLink } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  LayoutDashboard, Activity, GitFork, TrendingUp, Bot, Server, Zap, Clock
} from 'lucide-react';
import type { ConnectionStatus } from '../../types';

interface SidebarProps {
  status: ConnectionStatus;
  uptime?: string;
}

const navItems = [
  { to: '/',           label: 'Dashboard',       icon: LayoutDashboard, end: true },
  { to: '/monitoring', label: 'Monitoring',       icon: Activity },
  { to: '/topology',   label: 'Dependency Graph', icon: GitFork },
  { to: '/forecast',   label: 'Forecast',         icon: TrendingUp },
  { to: '/insights',   label: 'AI Insights',      icon: Bot },
];

const STATUS_CONFIG: Record<ConnectionStatus, { dot: string; text: string; label: string }> = {
  connected:    { dot: 'status-dot online',     text: 'text-white', label: 'Cluster Connected' },
  reconnecting: { dot: 'status-dot warning',    text: 'text-yellow-100', label: 'Reconnecting...' },
  disconnected: { dot: 'status-dot bg-red-500', text: 'text-red-100', label: 'Disconnected' },
};

export function Sidebar({ status, uptime }: SidebarProps) {
  const s = STATUS_CONFIG[status];

  return (
    <motion.aside
      initial={{ x: -20, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      transition={{ duration: 0.35 }}
      className="fixed left-0 top-0 h-full z-40 flex flex-col"
      style={{ width: 'var(--sidebar-width)' }}
    >
      <div
        className="flex flex-col h-full py-6 mx-3 my-3 rounded-3xl"
        style={{
          background: 'linear-gradient(135deg, #2563EB 0%, #3B82F6 50%, #06B6D4 100%)',
          backdropFilter: 'blur(20px)',
          WebkitBackdropFilter: 'blur(20px)',
          border: '1px solid rgba(255, 255, 255, 0.25)',
          boxShadow: '0 8px 32px 0 rgba(37, 99, 235, 0.2), inset 0 0 12px 0 rgba(255, 255, 255, 0.1)',
        }}
      >
        {/* Logo */}
        <div className="px-5 pb-6 border-b border-white/10">
          <div className="flex items-center gap-3 mb-1">
            <div className="p-2 bg-white/15 rounded-xl border border-white/10">
              <Zap className="h-5 w-5 text-white" />
            </div>
            <div>
              <h1 className="text-base font-700 text-white tracking-tight">KubeSense</h1>
              <p className="text-[10px] text-white/60 font-500">v2.0 · Observability</p>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 pt-4 space-y-0.5 overflow-y-auto">
          {navItems.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `sidebar-nav-item ${isActive ? 'active' : ''}`
              }
            >
              {({ isActive }) => (
                <>
                  <Icon className={`h-4.5 w-4.5 flex-shrink-0 transition-colors ${isActive ? 'text-white' : 'text-white/60'}`} style={{ width: 18, height: 18 }} />
                  <span>{label}</span>
                  {isActive && (
                    <span className="ml-auto w-1.5 h-1.5 rounded-full bg-white shadow-[0_0_8px_#ffffff]" />
                  )}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Bottom status */}
        <div className="px-4 pt-4 border-t border-white/10 space-y-3">
          <div className="flex items-center gap-2">
            <span className={s.dot} />
            <span className={`text-xs font-600 ${s.text}`}>{s.label}</span>
          </div>
          {uptime && (
            <div className="flex items-center gap-2 text-xs text-white/70">
              <Clock className="h-3 w-3 text-white/70" />
              <span>Uptime: {uptime}</span>
            </div>
          )}
          <div className="flex items-center gap-2 text-xs text-white/70">
            <Server className="h-3 w-3 text-white/70" />
            <span className="truncate">minikube · tasksphere-app</span>
          </div>
        </div>
      </div>
    </motion.aside>
  );
}
