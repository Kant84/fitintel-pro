import { useEffect, useState } from 'react';
import { visitsApi } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { DoorOpen, DoorClosed, Users, Clock } from 'lucide-react';

export default function VisitsPage() {
  const [activeVisits, setActiveVisits] = useState<any[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [clientId, setClientId] = useState('');
  const [loading, setLoading] = useState(true);

  const fetchData = () => {
    setLoading(true);
    Promise.all([
      visitsApi.active().then((r) => setActiveVisits(r.data?.items || [])).catch(() => {}),
      visitsApi.statsToday().then((r) => setStats(r.data)).catch(() => {}),
    ]).finally(() => setLoading(false));
  };

  useEffect(() => { fetchData(); }, []);

  const handleEntry = () => {
    if (!clientId) return;
    visitsApi.entry({ client_id: clientId, access_method: 'manual' }).then(fetchData);
    setClientId('');
  };

  const handleExit = (visitId: string) => {
    visitsApi.exit({ visit_id: visitId }).then(fetchData);
  };

  return (
    <div className="space-y-4">
      {/* Entry control */}
      <Card>
        <CardHeader className="pb-3"><CardTitle className="text-base">Контроль входа</CardTitle></CardHeader>
        <CardContent>
          <div className="flex gap-2">
            <Input placeholder="ID клиента или QR-код..." value={clientId} onChange={(e) => setClientId(e.target.value)} />
            <Button className="bg-emerald-600 hover:bg-emerald-700" onClick={handleEntry}>
              <DoorOpen className="w-4 h-4 mr-1" /> Вход
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardContent className="p-4 flex items-center gap-3">
            <div className="p-2 bg-emerald-50 rounded-lg"><Users className="w-5 h-5 text-emerald-600" /></div>
            <div>
              <p className="text-sm text-slate-500">В зале сейчас</p>
              <p className="text-xl font-bold">{activeVisits.length}</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 flex items-center gap-3">
            <div className="p-2 bg-blue-50 rounded-lg"><DoorOpen className="w-5 h-5 text-blue-600" /></div>
            <div>
              <p className="text-sm text-slate-500">Входов сегодня</p>
              <p className="text-xl font-bold">{stats?.entries || 0}</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 flex items-center gap-3">
            <div className="p-2 bg-amber-50 rounded-lg"><Clock className="w-5 h-5 text-amber-600" /></div>
            <div>
              <p className="text-sm text-slate-500">Ср. время</p>
              <p className="text-xl font-bold">{stats?.avg_duration ? `${Math.round(stats.avg_duration)} мин` : '-'}</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Active visits */}
      <Card>
        <CardHeader className="pb-3"><CardTitle className="text-base">Активные посещения</CardTitle></CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <div className="p-4 space-y-3">{[1, 2, 3].map((i) => <Skeleton key={i} className="h-14" />)}</div>
          ) : (
            <div className="divide-y">
              {activeVisits.map((v) => (
                <div key={v.id} className="p-4 flex items-center justify-between hover:bg-slate-50">
                  <div>
                    <p className="font-medium text-sm">{v.client_name || v.client_id}</p>
                    <p className="text-xs text-slate-500">Вход: {v.entry_time ? new Date(v.entry_time).toLocaleTimeString('ru-RU') : '-'}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="text-emerald-600 border-emerald-600">В зале</Badge>
                    <Button size="sm" variant="outline" onClick={() => handleExit(v.id)}>
                      <DoorClosed className="w-3 h-3 mr-1" /> Выход
                    </Button>
                  </div>
                </div>
              ))}
              {activeVisits.length === 0 && <p className="p-8 text-center text-slate-400">Нет активных посещений</p>}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
