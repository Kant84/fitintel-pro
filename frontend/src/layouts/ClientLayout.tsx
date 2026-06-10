import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/store/authStore';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { LogOut, User, CreditCard, DoorOpen, Wallet, Dumbbell } from 'lucide-react';

const clientNav = [
  { path: '/cabinet', label: 'Профиль', icon: User },
  { path: '/cabinet/subscriptions', label: 'Абонементы', icon: CreditCard },
  { path: '/cabinet/visits', label: 'Посещения', icon: DoorOpen },
  { path: '/cabinet/wallet', label: 'Кошелек', icon: Wallet },
];

export default function ClientLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Top bar */}
      <header className="bg-white border-b sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-emerald-500 rounded-lg flex items-center justify-center">
              <Dumbbell className="w-5 h-5 text-white" />
            </div>
            <span className="font-bold text-lg text-slate-800">FitIntel</span>
            <Badge variant="outline" className="text-emerald-600 border-emerald-600">Личный кабинет</Badge>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-sm text-slate-600">{user?.username || user?.email}</span>
            <Button variant="ghost" size="sm" onClick={() => { logout(); navigate('/login'); }}>
              <LogOut className="w-4 h-4 mr-1" /> Выход
            </Button>
          </div>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-4 py-6 flex gap-6">
        {/* Side nav */}
        <aside className="w-56 shrink-0">
          <nav className="space-y-1 bg-white rounded-xl border p-2">
            {clientNav.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.path;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                    isActive ? 'bg-emerald-50 text-emerald-700 font-medium' : 'text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </aside>

        {/* Content */}
        <main className="flex-1 min-w-0">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
