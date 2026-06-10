import { useEffect, useState } from 'react';
import { selfserviceApi } from '@/lib/api';
import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { DoorOpen, Clock } from 'lucide-react';

export default function ClientVisitsPage() {
  const [visits, setVisits] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    selfserviceApi.visits()
      .then((r) => setVisits(r.data?.items || []))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold flex items-center gap-2"><DoorOpen className="w-5 h-5" /> Мои посещения</h2>
      {loading ? (
        <div className="space-y-3">{[1, 2, 3].map((i) => <Skeleton key={i} className="h-16" />)}</div>
      ) : (
        <div className="space-y-2">
          {visits.map((v) => (
            <Card key={v.id}>
              <CardContent className="p-4 flex items-center justify-between">
                <div className="text-sm">
                  <p className="font-medium">{new Date(v.entry_time).toLocaleDateString('ru-RU', { weekday: 'long', day: 'numeric', month: 'long' })}</p>
                  <p className="text-slate-500 text-xs">Вход: {new Date(v.entry_time).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}</p>
                  {v.exit_time && <p className="text-slate-500 text-xs">Выход: {new Date(v.exit_time).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}</p>}
                </div>
                <div className="flex items-center gap-1 text-sm text-slate-600">
                  <Clock className="w-4 h-4" />
                  {v.duration_minutes ? `${v.duration_minutes} мин` : 'В зале'}
                </div>
              </CardContent>
            </Card>
          ))}
          {visits.length === 0 && <Card><CardContent className="p-8 text-center text-slate-400">Нет посещений</CardContent></Card>}
        </div>
      )}
    </div>
  );
}
