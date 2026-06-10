import { useEffect, useState } from 'react';
import { financeApi } from '@/lib/api';
import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Wallet, ArrowDownLeft, ArrowUpRight } from 'lucide-react';

export default function ClientWalletPage() {
  const [wallet, setWallet] = useState<any>(null);
  const [txs, setTxs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      financeApi.walletMe().then((r) => setWallet(r.data)),
      financeApi.walletTransactions().then((r) => setTxs(r.data?.items || [])),
    ]).finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-4">
      {loading ? <Skeleton className="h-32" /> : (
        <Card className="bg-emerald-600 text-white">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-emerald-100 text-sm">Баланс кошелька</p>
                <p className="text-3xl font-bold">{wallet?.balance || 0} {wallet?.currency || 'RUB'}</p>
              </div>
              <Wallet className="w-10 h-10 text-emerald-200" />
            </div>
          </CardContent>
        </Card>
      )}

      <h3 className="font-medium text-slate-700">История операций</h3>
      {loading ? (
        <div className="space-y-3">{[1, 2, 3].map((i) => <Skeleton key={i} className="h-14" />)}</div>
      ) : (
        <div className="space-y-2">
          {txs.map((tx) => (
            <Card key={tx.id}>
              <CardContent className="p-3 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className={`p-1.5 rounded-full ${tx.amount > 0 ? 'bg-emerald-50' : 'bg-red-50'}`}>
                    {tx.amount > 0 ? <ArrowDownLeft className="w-4 h-4 text-emerald-600" /> : <ArrowUpRight className="w-4 h-4 text-red-600" />}
                  </div>
                  <div className="text-sm">
                    <p>{tx.description || tx.type}</p>
                    <p className="text-xs text-slate-500">{tx.created_at ? new Date(tx.created_at).toLocaleDateString('ru-RU') : ''}</p>
                  </div>
                </div>
                <span className={`font-medium ${tx.amount > 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                  {tx.amount > 0 ? '+' : ''}{tx.amount} {tx.currency || 'RUB'}
                </span>
              </CardContent>
            </Card>
          ))}
          {txs.length === 0 && <p className="text-center text-slate-400 py-8">Нет операций</p>}
        </div>
      )}
    </div>
  );
}
