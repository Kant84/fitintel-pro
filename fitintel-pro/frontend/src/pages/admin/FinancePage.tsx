import { useEffect, useState } from 'react';
import { financeApi } from '@/lib/api';
import { Card, CardContent } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import { Wallet, CreditCard, Receipt } from 'lucide-react';

export default function FinancePage() {
  const [wallet, setWallet] = useState<any>(null);
  const [payments, setPayments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      financeApi.walletMe().then((r) => setWallet(r.data)).catch(() => {}),
      financeApi.payments().then((r) => setPayments(r.data?.items || [])).catch(() => {}),
    ]).finally(() => setLoading(false));
  }, []);

  const statusMap: Record<string, string> = {
    PENDING: 'bg-amber-100 text-amber-700',
    COMPLETED: 'bg-emerald-100 text-emerald-700',
    FAILED: 'bg-red-100 text-red-700',
    REFUNDED: 'bg-slate-100 text-slate-700',
  };

  return (
    <Tabs defaultValue="wallet" className="space-y-4">
      <TabsList>
        <TabsTrigger value="wallet"><Wallet className="w-4 h-4 mr-1" /> Кошельки</TabsTrigger>
        <TabsTrigger value="payments"><CreditCard className="w-4 h-4 mr-1" /> Платежи</TabsTrigger>
        <TabsTrigger value="receipts"><Receipt className="w-4 h-4 mr-1" /> Чеки</TabsTrigger>
      </TabsList>

      <TabsContent value="wallet" className="space-y-4">
        {loading ? <Skeleton className="h-32" /> : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card>
              <CardContent className="p-5">
                <p className="text-sm text-slate-500">Баланс</p>
                <p className="text-2xl font-bold">{wallet?.balance || 0} {wallet?.currency || 'RUB'}</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-5">
                <p className="text-sm text-slate-500">Заморожено</p>
                <p className="text-2xl font-bold">{wallet?.frozen_balance || 0}</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-5">
                <p className="text-sm text-slate-500">Транзакций</p>
                <p className="text-2xl font-bold">{wallet?.transaction_count || 0}</p>
              </CardContent>
            </Card>
          </div>
        )}
      </TabsContent>

      <TabsContent value="payments">
        <Card>
          <CardContent className="p-0">
            {loading ? (
              <div className="p-4 space-y-3">{[1, 2, 3].map((i) => <Skeleton key={i} className="h-14" />)}</div>
            ) : (
              <div className="divide-y">
                {payments.map((p) => (
                  <div key={p.id} className="p-4 flex items-center justify-between hover:bg-slate-50">
                    <div>
                      <p className="text-sm font-medium">{p.description || `Платеж #${p.id?.slice(0, 8)}`}</p>
                      <p className="text-xs text-slate-500">{p.client_name || p.client_id}</p>
                    </div>
                    <div className="flex items-center gap-3">
                      <p className="font-semibold">{p.amount} {p.currency || 'RUB'}</p>
                      <Badge className={statusMap[p.status] || 'bg-slate-100'}>{p.status}</Badge>
                    </div>
                  </div>
                ))}
                {payments.length === 0 && <p className="p-8 text-center text-slate-400">Нет платежей</p>}
              </div>
            )}
          </CardContent>
        </Card>
      </TabsContent>

      <TabsContent value="receipts">
        <Card>
          <CardContent className="p-8 text-center text-slate-400">
            <Receipt className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p>Выберите платеж для просмотра чека</p>
          </CardContent>
        </Card>
      </TabsContent>
    </Tabs>
  );
}
