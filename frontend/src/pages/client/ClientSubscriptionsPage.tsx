import { useEffect, useState } from 'react';
import { selfserviceApi } from '@/lib/api';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { CreditCard, Calendar, Check } from 'lucide-react';

export default function ClientSubscriptionsPage() {
  const [subs, setSubs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    selfserviceApi.subscriptions()
      .then((r) => setSubs(r.data?.items || []))
      .finally(() => setLoading(false));
  }, []);

  const statusMap: Record<string, string> = {
    ACTIVE: 'bg-emerald-100 text-emerald-700',
    FROZEN: 'bg-blue-100 text-blue-700',
    EXPIRED: 'bg-slate-100 text-slate-700',
    CANCELLED: 'bg-red-100 text-red-700',
  };

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold flex items-center gap-2"><CreditCard className="w-5 h-5" /> Мои абонементы</h2>
      {loading ? (
        <div className="space-y-3">{[1, 2].map((i) => <Skeleton key={i} className="h-28" />)}</div>
      ) : (
        <div className="space-y-3">
          {subs.map((s) => (
            <Card key={s.id}>
              <CardContent className="p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <p className="font-medium">{s.tariff_name}</p>
                  <Badge className={statusMap[s.status] || 'bg-slate-100'}>{s.status}</Badge>
                </div>
                <div className="text-sm text-slate-500 space-y-1">
                  <p className="flex items-center gap-2"><Calendar className="w-3 h-3" /> {s.start_date} — {s.end_date}</p>
                  <p className="flex items-center gap-2"><Check className="w-3 h-3" /> Осталось визитов: {s.visits_left}</p>
                  {s.freeze_until && <p className="text-blue-600">Заморожен до: {s.freeze_until}</p>}
                </div>
              </CardContent>
            </Card>
          ))}
          {subs.length === 0 && <Card><CardContent className="p-8 text-center text-slate-400">Нет абонементов</CardContent></Card>}
        </div>
      )}
    </div>
  );
}
