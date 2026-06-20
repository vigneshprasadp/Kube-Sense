import type { ConnectionStatus } from '../../types';

interface NavbarProps {
  status: ConnectionStatus;
}

export function Navbar({ status }: NavbarProps) {
  return (
    <header
      className="fixed top-0 right-0 z-30 flex items-center justify-end px-6 h-[var(--navbar-height)]"
      style={{
        left: 'calc(var(--sidebar-width) + 12px)',
        background: 'rgba(248,250,252,0.85)',
        backdropFilter: 'blur(12px)',
        WebkitBackdropFilter: 'blur(12px)',
        borderBottom: '1px solid rgba(0,0,0,0.06)',
      }}
    >
      {/* Cluster status badge only */}
      <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-600
        ${status === 'connected' ? 'bg-success-50 border-success-100 text-success-700' :
          status === 'reconnecting' ? 'bg-warning-50 border-warning-100 text-warning-700' :
          'bg-danger-50 border-danger-100 text-danger-700'}`}>
        <span className={`status-dot ${status === 'connected' ? 'online' : status === 'reconnecting' ? 'warning' : 'bg-danger-600'} !w-1.5 !h-1.5`} />
        {status === 'connected' ? 'Cluster Online' : status === 'reconnecting' ? 'Reconnecting' : 'Offline'}
      </div>
    </header>
  );
}
