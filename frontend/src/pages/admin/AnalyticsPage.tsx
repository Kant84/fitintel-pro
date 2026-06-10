import { useState } from 'react';
import { analyticsApi } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { BarChart3, TrendingUp } from 'lucide-react';

export default function AnalyticsPage() {
  const [start, setStart] = useState('');
  const [end, setEnd] = useState('');
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const fetchVisits = () => {
    if (!start || !end) return;
    setLoading(true);
    analyticsApi.visits(start, end).then((r) => setData(r.data)).finally(() => setLoading(false));
  };

  const maxVisits = Math.max(...(data?.daily?.map((d: any) => d.visits) || [1]), 1);

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader><CardTitle className="text-base">Аналитика посещений</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          <div className="flex gap-2">
            <Input type="date" value={start} onChange={(e) => setStart(e.target.value)} />
            <Input type="date" value={end} onChange={(e) => setEnd(e.target.value)} />
            <Button onClick={fetchVisits} className="bg-emerald-600 hover:bg-emerald-700"><BarChart3 className="w-4 h-4 mr-1" /> Показать</Button>
          </div>

          {loading && <Skeleton className="h-48" />}

          {data && !loading && (
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-sm">
                <TrendingUp className="w-4 h-4 text-emerald-600" />
                <span>Всего посещений: <strong>{data.total_visits}</strong></span>
              </div>
              <div className="space-y-2">
                {data.daily?.map((day: any) => (
                  <div key={day.day} className="flex items-center gap-3">
                    <span className="text-xs w-20 text-slate-500">{new Date(day.day).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' })}</span>
                    <div className="flex-1 bg-slate-100 rounded-full h-6 overflow-hidden">
                      <div className="bg-emerald-500 h-full rounded-full flex items-center justify-end pr-2 transition-all" style={{ width: `${Math.max((day.visits / maxVisits) * 100, 5)}%` }}>
                        {day.visits > 0 && <span className="text-[10px] text-white font-medium">{day.visits}</span>}
                      </div>
                    </div>
                    <span className="text-xs w-10 text-slate-400">{day.unique_clients} чел</span>
                  </div>
                ))}
                {data.daily?.length === 0 && <p className="text-sm text-slate-400">Нет данных</p>}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
