import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { useAuthStore } from '@/store/authStore';
import { Shield, Server } from 'lucide-react';

export default function SettingsPage() {
  const { user } = useAuthStore();

  return (
    <div className="max-w-2xl space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Shield className="w-4 h-4" />
            Мой профиль
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div><span className="text-slate-500">ID:</span> <span className="font-mono">{user?.id}</span></div>
            <div><span className="text-slate-500">Логин:</span> {user?.username || '-'}</div>
            <div><span className="text-slate-500">Email:</span> {user?.email || '-'}</div>
            <div><span className="text-slate-500">Статус:</span> <Badge variant={user?.is_active ? 'default' : 'secondary'}>{user?.is_active ? 'Активен' : 'Неактивен'}</Badge></div>
          </div>
          <Separator />
          <div>
            <span className="text-sm text-slate-500">Роли:</span>
            <div className="flex flex-wrap gap-1 mt-1">
              {user?.roles?.map((r) => <Badge key={r} variant="outline">{r}</Badge>)}
            </div>
          </div>
          <div>
            <span className="text-sm text-slate-500">Права ({user?.permissions?.length || 0}):</span>
            <div className="flex flex-wrap gap-1 mt-1 max-h-24 overflow-y-auto">
              {user?.permissions?.map((p) => <Badge key={p} variant="secondary" className="text-[10px]">{p}</Badge>)}
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Server className="w-4 h-4" />
            Система
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <div className="flex justify-between"><span className="text-slate-500">Версия API</span><span>v1.0.0</span></div>
          <div className="flex justify-between"><span className="text-slate-500">Среда</span><Badge>production</Badge></div>
          <div className="flex justify-between"><span className="text-slate-500">Временная зона</span><span>Europe/Moscow</span></div>
        </CardContent>
      </Card>
    </div>
  );
}
