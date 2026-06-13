import { useEffect, useState } from 'react';
import { clientsApi } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Plus, Search, Phone, Mail } from 'lucide-react';

export default function ClientsPage() {
  const [clients, setClients] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState({ first_name: '', last_name: '', phone: '', email: '', status: 'ACTIVE' });

  const fetchClients = () => {
    setLoading(true);
    clientsApi.list({ limit: 100 })
      .then((res) => setClients(res.data?.items || []))
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchClients(); }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    await clientsApi.create({ ...form, is_active: true, gender: 'unknown', client_category: 'standard' });
    setDialogOpen(false);
    setForm({ first_name: '', last_name: '', phone: '', email: '', status: 'ACTIVE' });
    fetchClients();
  };

  const filtered = clients.filter((c) =>
    `${c.first_name} ${c.last_name} ${c.phone} ${c.email}`.toLowerCase().includes(search.toLowerCase())
  );

  const statusBadge = (status: string) => {
    const map: Record<string, string> = {
      ACTIVE: 'bg-emerald-100 text-emerald-700',
      BLOCKED: 'bg-red-100 text-red-700',
      FROZEN: 'bg-blue-100 text-blue-700',
    };
    return <Badge className={map[status] || 'bg-slate-100'}>{status}</Badge>;
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <Input placeholder="Поиск клиентов..." value={search} onChange={(e) => setSearch(e.target.value)} className="pl-9" />
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button className="bg-emerald-600 hover:bg-emerald-700">
              <Plus className="w-4 h-4 mr-1" /> Добавить клиента
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader><DialogTitle>Новый клиент</DialogTitle></DialogHeader>
            <form onSubmit={handleCreate} className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1"><Label>Имя</Label><Input required value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} /></div>
                <div className="space-y-1"><Label>Фамилия</Label><Input required value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} /></div>
              </div>
              <div className="space-y-1"><Label>Телефон</Label><Input required value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} placeholder="+79991234567" /></div>
              <div className="space-y-1"><Label>Email</Label><Input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></div>
              <Button type="submit" className="w-full bg-emerald-600 hover:bg-emerald-700">Создать</Button>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className="p-4 space-y-3">
              {[1, 2, 3, 4, 5].map((i) => <Skeleton key={i} className="h-14" />)}
            </div>
          ) : (
            <div className="divide-y">
              {filtered.map((client) => (
                <div key={client.id} className="p-4 flex items-center justify-between hover:bg-slate-50 transition-colors">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-slate-200 flex items-center justify-center text-sm font-medium text-slate-600">
                      {client.first_name?.[0]}{client.last_name?.[0]}
                    </div>
                    <div>
                      <p className="font-medium text-sm">{client.first_name} {client.last_name}</p>
                      <div className="flex items-center gap-3 text-xs text-slate-500">
                        <span className="flex items-center gap-1"><Phone className="w-3 h-3" />{client.phone}</span>
                        {client.email && <span className="flex items-center gap-1"><Mail className="w-3 h-3" />{client.email}</span>}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {statusBadge(client.status)}
                    <span className="text-xs text-slate-400">{client.is_active ? 'Активен' : 'Неактивен'}</span>
                  </div>
                </div>
              ))}
              {filtered.length === 0 && <p className="p-8 text-center text-slate-400">Клиенты не найдены</p>}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
