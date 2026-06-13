import { useEffect, useState } from 'react';
import { subscriptionsApi } from '@/lib/api';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { CreditCard, Pause, Play, RotateCcw, X } from 'lucide-react';

export default function SubscriptionsPage() {
  const [subs, setSubs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const fetch = () => {
    setLoading(true);
    subscriptionsApi.list({ limit: 100 })
      .then((res) => setSubs(res.data?.items || []))
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetch(); }, []);

  const statusMap: Record<string, string> = {
    ACTIVE: 'bg-emerald-100 text-emerald-700',
    FROZEN: 'bg-blue-100 text-blue-700',
    EXPIRED: 'bg-slate-100 text-slate-700',
    CANCELLED: 'bg-red-100 text-red-700',
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Абонементы</h2>
        <Button size="sm" className="bg-emerald-600 hover:bg-emerald-700">
          <CreditCard className="w-4 h-4 mr-1" /> Новый абонемент
        </Button>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => <Skeleton key={i} className="h-40" />)}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {subs.map((s) => (
            <Card key={s.id}>
              <CardContent className="p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <Badge className={statusMap[s.status] || 'bg-slate-100'}>{s.status}</Badge>
                  <span className="text-xs text-slate-400">{s.visits_left} визитов</span>
                </div>
                <div>
                  <p className="font-medium">{s.tariff_name || 'Тариф'}</p>
                  <p className="text-xs text-slate-500">Клиент: {s.client_name || s.client_id}</p>
                </div>
                <div className="text-xs text-slate-500 space-y-1">
                  <p>С: {s.start_date ? new Date(s.start_date).toLocaleDateString('ru-RU') : '-'}</p>
                  <p>По: {s.end_date ? new Date(s.end_date).toLocaleDateString('ru-RU') : '-'}</p>
                </div>
                <div className="flex gap-1 pt-1">
                  {s.status === 'ACTIVE' && (
                    <Button size="sm" variant="outline" onClick={() => subscriptionsApi.freeze(s.id).then(fetch)}>
                      <Pause className="w-3 h-3 mr-1" /> Заморозить
                    </Button>
                  )}
                  {s.status === 'FROZEN' && (
                    <Button size="sm" variant="outline" onClick={() => subscriptionsApi.unfreeze(s.id).then(fetch)}>
                      <Play className="w-3 h-3 mr-1" /> Разморозить
                    </Button>
                  )}
                  <Button size="sm" variant="outline" onClick={() => subscriptionsApi.renew(s.id).then(fetch)}>
                    <RotateCcw className="w-3 h-3 mr-1" /> Продлить
                  </Button>
                  <Button size="sm" variant="outline" className="text-red-600" onClick={() => subscriptionsApi.cancel(s.id).then(fetch)}>
                    <X className="w-3 h-3" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
          {subs.length === 0 && <p className="col-span-full text-center text-slate-400 py-12">Нет абонементов</p>}
        </div>
      )}
    </div>
  );
}
