import { useState } from 'react';
import { accessApi } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { QrCode, DoorOpen, Lock } from 'lucide-react';

export default function AccessPage() {
  const [credential, setCredential] = useState('');
  const [deviceId, setDeviceId] = useState('');
  const [checkResult, setCheckResult] = useState<any>(null);
  const [clientId, setClientId] = useState('');

  const handleCheck = async () => {
    if (!credential) return;
    const res = await accessApi.check({ credential, device_id: deviceId || undefined });
    setCheckResult(res.data);
  };

  const handleGrant = async () => {
    if (!credential) return;
    await accessApi.grant({ credential, device_id: deviceId || undefined });
    setCheckResult({ status: 'granted', message: 'Доступ предоставлен' });
  };

  return (
    <Tabs defaultValue="check" className="space-y-4">
      <TabsList>
        <TabsTrigger value="check"><DoorOpen className="w-4 h-4 mr-1" /> Проверка</TabsTrigger>
        <TabsTrigger value="credentials"><QrCode className="w-4 h-4 mr-1" /> Ключи</TabsTrigger>
        <TabsTrigger value="lockers"><Lock className="w-4 h-4 mr-1" /> Шкафчики</TabsTrigger>
      </TabsList>

      <TabsContent value="check" className="space-y-4">
        <Card>
          <CardHeader className="pb-3"><CardTitle className="text-base">Проверка доступа</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <Input placeholder="QR-код или RFID..." value={credential} onChange={(e) => setCredential(e.target.value)} />
            <Input placeholder="ID устройства (опционально)" value={deviceId} onChange={(e) => setDeviceId(e.target.value)} />
            <div className="flex gap-2">
              <Button variant="outline" onClick={handleCheck}>Проверить</Button>
              <Button className="bg-emerald-600 hover:bg-emerald-700" onClick={handleGrant}>
                <DoorOpen className="w-4 h-4 mr-1" /> Открыть
              </Button>
            </div>
            {checkResult && (
              <div className={`p-3 rounded-lg ${checkResult.allowed || checkResult.status === 'granted' ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700'}`}>
                <p className="font-medium">{checkResult.allowed || checkResult.status === 'granted' ? '✓ Доступ разрешен' : '✗ Доступ запрещен'}</p>
                {checkResult.message && <p className="text-sm">{checkResult.message}</p>}
              </div>
            )}
          </CardContent>
        </Card>
      </TabsContent>

      <TabsContent value="credentials" className="space-y-4">
        <Card>
          <CardHeader className="pb-3"><CardTitle className="text-base">Управление ключами</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <Input placeholder="ID клиента" value={clientId} onChange={(e) => setClientId(e.target.value)} />
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => accessApi.qrGet(clientId)} disabled={!clientId}>Показать QR</Button>
              <Button variant="outline" onClick={() => accessApi.qrCreate({ client_id: clientId })} disabled={!clientId}>Создать QR</Button>
            </div>
          </CardContent>
        </Card>
      </TabsContent>

      <TabsContent value="lockers">
        <Card>
          <CardContent className="p-8 text-center text-slate-400">
            <Lock className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p>Управление шкафчиками</p>
          </CardContent>
        </Card>
      </TabsContent>
    </Tabs>
  );
}
