import { useEffect, useState } from 'react';
import { devicesApi } from '@/lib/api';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Wifi, WifiOff, RefreshCw } from 'lucide-react';

export default function DevicesPage() {
  const [devices, setDevices] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const fetch = () => {
    setLoading(true);
    devicesApi.list().then((r) => setDevices(r.data?.items || [])).finally(() => setLoading(false));
  };

  useEffect(() => { fetch(); }, []);

  const isOnline = (lastPing: string | null) => {
    if (!lastPing) return false;
    const diff = Date.now() - new Date(lastPing).getTime();
    return diff < 5 * 60 * 1000; // 5 min
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Устройства</h2>
        <Button size="sm" variant="outline" onClick={fetch}><RefreshCw className="w-4 h-4 mr-1" /> Обновить</Button>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {loading ? [1, 2, 3].map((i) => <Skeleton key={i} className="h-32" />) : (
          devices.map((d) => {
            const online = isOnline(d.last_ping);
            return (
              <Card key={d.id}>
                <CardContent className="p-4 space-y-2">
                  <div className="flex items-center justify-between">
                    <p className="font-medium">{d.name}</p>
                    {online ? <Wifi className="w-4 h-4 text-emerald-500" /> : <WifiOff className="w-4 h-4 text-red-500" />}
                  </div>
                  <p className="text-xs text-slate-500">{d.device_type} — {d.location}</p>
                  <Badge className={online ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'}>
                    {online ? 'Онлайн' : 'Оффлайн'}
                  </Badge>
                  <p className="text-xs text-slate-400">Last ping: {d.last_ping ? new Date(d.last_ping).toLocaleString('ru-RU') : 'Никогда'}</p>
                  <Button size="sm" variant="outline" onClick={() => devicesApi.ping(d.id)}>Ping</Button>
                </CardContent>
              </Card>
            );
          })
        )}
        {!loading && devices.length === 0 && (
          <Card className="col-span-full"><CardContent className="p-8 text-center text-slate-400">Нет устройств</CardContent></Card>
        )}
      </div>
    </div>
  );
}
