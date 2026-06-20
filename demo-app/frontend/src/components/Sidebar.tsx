import { 
  LayoutDashboard, 
  Activity, 
  GitFork, 
  TrendingUp, 
  Bot, 
  Server
} from 'lucide-react';

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  backendOnline: boolean;
}

export const Sidebar: React.FC<SidebarProps> = ({ activeTab, setActiveTab, backendOnline }) => {
  const menuItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'monitoring', label: 'Monitoring', icon: Activity },
    { id: 'topology', label: 'Dependency Graph', icon: GitFork },
    { id: 'forecast', label: 'Forecast', icon: TrendingUp },
    { id: 'insights', label: 'AI Insights', icon: Bot },
  ];

  return (
    <aside className="w-64 bg-white border-r border-gray-200 flex flex-col h-screen sticky top-0">
      <div className="p-6 border-b border-gray-100 flex flex-col gap-1">
        <div className="flex items-center gap-2">
          <Server className="h-6 w-6 text-brand-600" />
          <h1 className="text-xl font-bold text-gray-900 tracking-tight">KubeSense</h1>
        </div>
        <p className="text-xs text-gray-400 font-medium">Kubernetes AI Observability</p>
      </div>

      <nav className="flex-1 px-4 py-6 space-y-1">
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`w-full flex items-center gap-3 px-4 py-3 text-sm font-medium rounded-lg transition-all ${
                isActive 
                  ? 'bg-brand-50 text-brand-700 shadow-sm' 
                  : 'text-gray-500 hover:bg-gray-50 hover:text-gray-900'
              }`}
            >
              <Icon className={`h-5 w-5 ${isActive ? 'text-brand-600' : 'text-gray-400'}`} />
              {item.label}
            </button>
          );
        })}
      </nav>

      <div className="p-4 border-t border-gray-100 bg-gray-50/50">
        <div className="flex items-center gap-2">
          <span className={`h-2.5 w-2.5 rounded-full ${backendOnline ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
          <span className="text-xs font-semibold text-gray-600">
            {backendOnline ? 'Cluster Connected' : 'Disconnected'}
          </span>
        </div>
      </div>
    </aside>
  );
};
