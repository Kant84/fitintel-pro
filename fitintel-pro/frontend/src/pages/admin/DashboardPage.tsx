import { useEffect, useState } from 'react';
import { analyticsApi } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Users, DoorOpen, CreditCard, Wallet, TrendingUp, Activity } from 'lucide-react';

export default function DashboardPage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    analyticsApi.dashboard()
      .then((res) => setData(res.data))
      .finally(() => setLoading(false));
  }, []);

  const stats = [
    { label: 'Всего клиентов', value: data?.clients?.total || 0, sub: `${data?.clients?.active || 0} активных`, icon: Users, color: 'bg-blue-50 text-blue-600' },
    { label: 'Посещений сегодня', value: data?.visits_today || 0, sub: 'за сегодня', icon: DoorOpen, color: 'bg-emerald-50 text-emerald-600' },
    { label: 'Активных абонементов', value: data?.subscriptions_active || 0, sub: 'абонементы', icon: CreditCard, color: 'bg-purple-50 text-purple-600' },
    { label: 'Выручка (мес)', value: `${(data?.revenue_month || 0).toLocaleString('ru-RU')} ₽`, sub: 'с начала месяца', icon: Wallet, color: 'bg-amber-50 text-amber-600' },
  ];

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-28" />)}
        </div>
        <Skeleton className="h-64" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((s) => {
          const Icon = s.icon;
          return (
            <Card key={s.label}>
              <CardContent className="p-5">
                <div className="flex items-start justify-between">
                  <div className="space-y-1">
                    <p className="text-sm text-slate-500">{s.label}</p>
                    <p className="text-2xl font-bold text-slate-800">{s.value}</p>
                    <p className="text-xs text-slate-400">{s.sub}</p>
                  </div>
                  <div className={`p-2.5 rounded-lg ${s.color}`}>
                    <Icon className="w-5 h-5" />
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Quick actions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Activity className="w-4 h-4" />
              Быстрые действия
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="grid grid-cols-2 gap-2">
              <QuickAction label="Новый клиент" path="/clients" desc="Регистрация" />
              <QuickAction label="Продажа" path="/finance" desc="Абонемент / услуга" />
              <QuickAction label="Вход клиента" path="/visits" desc="Зафиксировать" />
              <QuickAction label="Проверить доступ" path="/access" desc="QR / RFID" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <TrendingUp className="w-4 h-4" />
              Статус системы
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <StatusRow label="API" status="online" />
            <StatusRow label="База данных" status="online" />
            <StatusRow label="Redis" status="online" />
            <StatusRow label="Celery Worker" status="online" />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function QuickAction({ label, path, desc }: { label: string; path: string; desc: string }) {
  return (
    <a href={path} className="block p-3 rounded-lg border hover:bg-slate-50 transition-colors">
      <p className="font-medium text-sm text-slate-800">{label}</p>
      <p className="text-xs text-slate-500">{desc}</p>
    </a>
  );
}

function StatusRow({ label, status }: { label: string; status: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-sm text-slate-600">{label}</span>
      <Badge variant={status === 'online' ? 'default' : 'destructive'} className={status === 'online' ? 'bg-emerald-100 text-emerald-700 hover:bg-emerald-100' : ''}>
        {status === 'online' ? 'Работает' : 'Ошибка'}
      </Badge>
    </div>
  );
}
