import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/store/authStore';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import {
  LayoutDashboard, Users, CreditCard, DoorOpen, Wallet,
  Receipt, Settings, LogOut, Dumbbell, Bell, Shield,
  BarChart3, QrCode, FileText, Megaphone
} from 'lucide-react';

const navItems = [
  { path: '/', label: 'Дашборд', icon: LayoutDashboard },
  { path: '/clients', label: 'Клиенты', icon: Users },
  { path: '/subscriptions', label: 'Абонементы', icon: CreditCard },
  { path: '/visits', label: 'Посещения', icon: DoorOpen },
  { path: '/access', label: 'Доступ', icon: QrCode },
  { path: '/finance', label: 'Финансы', icon: Wallet },
  { path: '/receipts', label: 'Чеки', icon: Receipt },
  { path: '/cashdesk', label: 'Касса', icon: BarChart3 },
  { path: '/devices', label: 'Устройства', icon: Dumbbell },
  { path: '/analytics', label: 'Аналитика', icon: BarChart3 },
  { path: '/documents', label: 'Документы', icon: FileText },
  { path: '/marketing', label: 'Маркетинг', icon: Megaphone },
  { path: '/rbac', label: 'RBAC', icon: Shield },
  { path: '/settings', label: 'Настройки', icon: Settings },
];

export default function AdminLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="flex h-screen bg-slate-50">
      {/* Sidebar */}
      <aside className="w-64 bg-slate-900 text-white flex flex-col">
        <div className="p-4 flex items-center gap-3">
          <div className="w-8 h-8 bg-emerald-500 rounded-lg flex items-center justify-center">
            <Dumbbell className="w-5 h-5 text-white" />
          </div>
          <span className="font-bold text-lg">FitIntel Pro</span>
        </div>
        <Separator className="bg-slate-700" />
        <ScrollArea className="flex-1 py-2">
          <nav className="px-2 space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.path;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                    isActive
                      ? 'bg-emerald-600 text-white'
                      : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </ScrollArea>
        <Separator className="bg-slate-700" />
        <div className="p-4 space-y-3">
          <div className="flex items-center gap-2 text-sm text-slate-400">
            <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center text-xs font-medium">
              {user?.username?.[0]?.toUpperCase() || 'U'}
            </div>
            <div className="flex-1 min-w-0">
              <p className="truncate text-white">{user?.username || 'User'}</p>
              <p className="truncate text-xs">{user?.email}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-1">
            {user?.roles?.map((role) => (
              <Badge key={role} variant="outline" className="text-[10px] border-slate-600 text-slate-400">
                {role}
              </Badge>
            ))}
          </div>
          <Button variant="ghost" size="sm" className="w-full text-slate-400 hover:text-white hover:bg-slate-800" onClick={handleLogout}>
            <LogOut className="w-4 h-4 mr-2" />
            Выход
          </Button>
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="h-14 bg-white border-b flex items-center justify-between px-6">
          <h1 className="text-lg font-semibold text-slate-800">
            {navItems.find((n) => n.path === location.pathname)?.label || 'FitIntel Pro'}
          </h1>
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="icon" className="relative">
              <Bell className="w-5 h-5" />
              <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full" />
            </Button>
            <Badge variant="secondary" className="bg-emerald-100 text-emerald-700">Online</Badge>
          </div>
        </header>
        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
