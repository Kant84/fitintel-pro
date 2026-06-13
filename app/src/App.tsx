import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useEffect } from 'react';
import { useAuthStore } from '@/store/authStore';
import AdminLayout from '@/layouts/AdminLayout';
import ClientLayout from '@/layouts/ClientLayout';
import LoginPage from '@/pages/auth/LoginPage';
import DashboardPage from '@/pages/admin/DashboardPage';
import ClientsPage from '@/pages/admin/ClientsPage';
import SubscriptionsPage from '@/pages/admin/SubscriptionsPage';
import VisitsPage from '@/pages/admin/VisitsPage';
import FinancePage from '@/pages/admin/FinancePage';
import AccessPage from '@/pages/admin/AccessPage';
import SettingsPage from '@/pages/admin/SettingsPage';
import DevicesPage from '@/pages/admin/DevicesPage';
import AnalyticsPage from '@/pages/admin/AnalyticsPage';
import ProfilePage from '@/pages/client/ProfilePage';
import ClientSubscriptionsPage from '@/pages/client/ClientSubscriptionsPage';
import ClientVisitsPage from '@/pages/client/ClientVisitsPage';
import ClientWalletPage from '@/pages/client/ClientWalletPage';

function AuthGuard({ children, requireAdmin = false }: { children: React.ReactNode; requireAdmin?: boolean }) {
  const { isAuthenticated, user, isLoading } = useAuthStore();

  if (isLoading) return <div className="min-h-screen flex items-center justify-center"><div className="animate-spin w-8 h-8 border-4 border-emerald-500 border-t-transparent rounded-full" /></div>;
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  if (requireAdmin && !user?.roles?.some((r: string) => ['owner', 'admin', 'manager'].includes(r))) return <Navigate to="/cabinet" replace />;
  return <>{children}</>;
}

function RedirectByRole() {
  const { user } = useAuthStore();
  const isAdmin = user?.roles?.some((r: string) => ['owner', 'admin', 'manager', 'cashier', 'trainer', 'support'].includes(r));
  return isAdmin ? <Navigate to="/" replace /> : <Navigate to="/cabinet" replace />;
}

export default function App() {
  const { isAuthenticated, fetchMe } = useAuthStore();

  useEffect(() => {
    if (isAuthenticated) fetchMe();
  }, [isAuthenticated]);

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />

        {/* Admin routes */}
        <Route path="/" element={<AuthGuard requireAdmin><AdminLayout /></AuthGuard>}>
          <Route index element={<DashboardPage />} />
          <Route path="clients" element={<ClientsPage />} />
          <Route path="subscriptions" element={<SubscriptionsPage />} />
          <Route path="visits" element={<VisitsPage />} />
          <Route path="finance" element={<FinancePage />} />
          <Route path="access" element={<AccessPage />} />
          <Route path="devices" element={<DevicesPage />} />
          <Route path="analytics" element={<AnalyticsPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="receipts" element={<FinancePage />} />
          <Route path="cashdesk" element={<FinancePage />} />
          <Route path="rbac" element={<SettingsPage />} />
          <Route path="documents" element={<SettingsPage />} />
          <Route path="marketing" element={<SettingsPage />} />
        </Route>

        {/* Client cabinet */}
        <Route path="/cabinet" element={<AuthGuard><ClientLayout /></AuthGuard>}>
          <Route index element={<ProfilePage />} />
          <Route path="subscriptions" element={<ClientSubscriptionsPage />} />
          <Route path="visits" element={<ClientVisitsPage />} />
          <Route path="wallet" element={<ClientWalletPage />} />
        </Route>

        <Route path="*" element={<RedirectByRole />} />
      </Routes>
    </BrowserRouter>
  );
}
