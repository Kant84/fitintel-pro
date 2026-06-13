import { useEffect, useState } from 'react';
import { selfserviceApi } from '@/lib/api';
import { useAuthStore } from '@/store/authStore';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { User, Wallet, CreditCard, Calendar } from 'lucide-react';

export default function ProfilePage() {
  const { user } = useAuthStore();
  const [profile, setProfile] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    selfserviceApi.profile()
      .then((r) => setProfile(r.data))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="space-y-4"><Skeleton className="h-32" /><Skeleton className="h-32" /></div>;

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <User className="w-4 h-4" />
            Профиль
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 rounded-full bg-emerald-100 flex items-center justify-center text-xl font-bold text-emerald-700">
              {profile?.client?.first_name?.[0] || user?.username?.[0] || '?'}
            </div>
            <div>
              <p className="font-semibold text-lg">{profile?.client?.first_name} {profile?.client?.last_name}</p>
              <p className="text-sm text-slate-500">{user?.email}</p>
              <Badge variant={profile?.client?.status === 'ACTIVE' ? 'default' : 'secondary'} className="mt-1">
                {profile?.client?.status === 'ACTIVE' ? 'Активен' : profile?.client?.status}
              </Badge>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div className="flex items-center gap-2 text-slate-600">
              <User className="w-4 h-4" /> {profile?.client?.phone || '-'}
            </div>
            <div className="flex items-center gap-2 text-slate-600">
              <Calendar className="w-4 h-4" /> С {profile?.client?.created_at ? new Date(profile.client.created_at).toLocaleDateString('ru-RU') : '-'}
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardContent className="p-5">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-emerald-50 rounded-lg"><Wallet className="w-5 h-5 text-emerald-600" /></div>
              <div>
                <p className="text-sm text-slate-500">Баланс кошелька</p>
                <p className="text-xl font-bold">{profile?.wallet?.balance || 0} {profile?.wallet?.currency || 'RUB'}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-5">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-50 rounded-lg"><CreditCard className="w-5 h-5 text-blue-600" /></div>
              <div>
                <p className="text-sm text-slate-500">Абонементов</p>
                <p className="text-xl font-bold">{profile?.subscriptions?.length || 0}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
