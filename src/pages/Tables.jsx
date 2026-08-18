import React, { useEffect, useState } from 'react';
import { api } from '@/lib/restaurant-context';
import { useRestaurant, userRestaurantId } from '@/lib/restaurant-context';
import { formatCurrency, timeAgo, todayISO } from '@/lib/format';
import { Plus, Loader2, X, Pencil, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogClose
} from '@/components/ui/dialog';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from '@/components/ui/select';
import { useToast } from '@/components/ui/use-toast';

const PAYMENTS = [
  { value: 'cash', label: 'Dinheiro' },
  { value: 'pix', label: 'Pix' },
  { value: 'card', label: 'Cartão' },
  { value: 'other', label: 'Outro' },
];

const STATUS = {
  free: { label: 'Livre', cls: 'bg-success/15 text-success border-success/30' },
  occupied: { label: 'Ocupada', cls: 'bg-primary/15 text-primary border-primary/30' },
  waiting: { label: 'Aguardando', cls: 'bg-warning/15 text-warning border-warning/30' },
  preparing: { label: 'Em preparo', cls: 'bg-accent/15 text-accent-foreground border-accent/30' },
  bill_requested: { label: 'Conta solicitada', cls: 'bg-destructive/15 text-destructive border-destructive/30' },
  closing: { label: 'Encerrando', cls: 'bg-secondary text-secondary-foreground border-border' },
};

export default function Tables() {
  const { user, restaurant } = useRestaurant();
  const rid = userRestaurantId(user);
  const { toast } = useToast();
  const [tables, setTables] = useState([]);
  const [orders, setOrders] = useState([]);
  const [itemsByOrder, setItemsByOrder] = useState({});
  const [loading, setLoading] = useState(true);
  const [addOpen, setAddOpen] = useState(false);
  const [editTable, setEditTable] = useState(null);
  const [comanda, setComanda] = useState(null);
  const [form, setForm] = useState({ number: '', seats: 4, qty: 1 });

  const load = async () => {
    if (!rid) { setLoading(false); return; }
    
    setLoading(true);
    try {
      // Carregar mesas e pedidos
      const [t, o] = await Promise.allSettled([
        api.Table.filter({ restaurant_id: rid }, 'number', 500),
        api.Order.filter({ restaurant_id: rid, status: { $in: ['received', 'preparing', 'ready', 'delivered'] } }, '-created_date', 500),
      ]);
      
      const tables_data = t.status === 'fulfilled' ? t.value : [];
      const orders_data = o.status === 'fulfilled' ? o.value : [];
      
      setTables(tables_data);
      setOrders(orders_data);

      // Carregar items para cada pedido
      if (orders_data.length > 0) {
        const map = {};
        await Promise.all(orders_data.map(async (ord) => {
          try {
            map[ord.id] = await api.OrderItem.filter({ order_id: ord.id });
          } catch (e) {
            map[ord.id] = [];
          }
        }));
        setItemsByOrder(map);
      } else {
        setItemsByOrder({});
      }
    } catch (err) {
      toast({ title: 'Erro ao carregar', description: err.message, variant: 'destructive' });
      setTables([]); setOrders([]); setItemsByOrder({});
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { if (rid) load(); }, [rid]);
  useEffect(() => {
    if (!rid) return;
    const unsub = api.Table.subscribe(() => load());
    return unsub;
  }, [rid]);

  const valueOf = (t) => {
    const o = orders.find((x) => x.id === t.current_order_id);
    return o ? Number(o.total || 0) : 0;
  };

  const openTable = async (t) => {
    const order = await api.Order.create({
      restaurant_id: rid, table_id: t.id, table_number: t.number,
      status: 'received', subtotal: 0, service_tax: 0, total: 0,
    });
    await api.Table.update(t.id, { status: 'occupied', current_order_id: order.id, opened_at: todayISO() });
    toast({ title: `Mesa ${t.number} aberta`, description: 'Comanda iniciada.' });
    load();
  };

  const closeTable = async (t) => {
    if (t.current_order_id) {
      await api.Order.update(t.current_order_id, { status: 'closed', closed_at: todayISO() });
    }
    await api.Table.update(t.id, { status: 'free', current_order_id: '', opened_at: '' });
    toast({ title: `Mesa ${t.number} encerrada` });
    load();
  };

  const saveTable = async () => {
    if (!form.number.trim()) { toast({ title: 'Informe o número inicial', variant: 'destructive' }); return; }
    if (editTable) {
      await api.Table.update(editTable.id, { number: form.number.trim(), seats: Number(form.seats) });
    } else {
      const qty = Math.max(1, Number(form.qty) || 1);
      const start = parseInt(form.number, 10);
      if (qty > 1 && !Number.isNaN(start)) {
        const rows = Array.from({ length: qty }, (_, i) => ({
          restaurant_id: rid, number: String(start + i).padStart(2, '0'), seats: Number(form.seats)
        }));
        await api.Table.bulkCreate(rows);
        toast({ title: `${qty} mesas criadas`, description: `${rows[0].number} a ${rows[rows.length - 1].number}` });
      } else {
        await api.Table.create({ restaurant_id: rid, number: form.number.trim(), seats: Number(form.seats) });
      }
    }
    setAddOpen(false); setEditTable(null); setForm({ number: '', seats: 4, qty: 1 });
    load();
  };

  const deleteTable = async (t) => {
    await api.Table.delete(t.id);
    load();
  };

  if (loading) return <div className="grid h-full place-items-center"><Loader2 className="h-7 w-7 animate-spin text-primary" /></div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-heading text-3xl font-semibold">Mesas</h1>
          <p className="text-sm text-muted-foreground">{tables.length} mesas · {tables.filter(t => t.status !== 'free').length} ocupadas</p>
        </div>
        <Button onClick={() => { setEditTable(null); setForm({ number: '', seats: 4, qty: 1 }); setAddOpen(true); }}>
          <Plus className="h-4 w-4" /> Nova mesa
        </Button>
      </div>

      {tables.length === 0 ? (
        <div className="surface-card grid h-56 place-items-center text-muted-foreground">
          <div className="text-center">
            <p className="font-medium text-foreground">Nenhuma mesa ainda</p>
            <p className="text-sm">Crie mesas para gerar os QR Codes.</p>
          </div>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {tables.map((t) => {
            const st = STATUS[t.status] || STATUS.free;
            return (
              <div key={t.id} className="surface-card p-4 transition hover:border-primary/40">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-heading text-xl font-semibold">Mesa {t.number}</p>
                    <p className="text-xs text-muted-foreground">{t.seats} lugares</p>
                  </div>
                  <span className={`rounded-full border px-2.5 py-1 text-xs font-medium ${st.cls}`}>{st.label}</span>
                </div>

                <div className="mt-4 space-y-1 text-sm">
                  <div className="flex justify-between"><span className="text-muted-foreground">Valor atual</span><span className="font-medium">{formatCurrency(valueOf(t), restaurant?.currency)}</span></div>
                  <div className="flex justify-between"><span className="text-muted-foreground">Aberta há</span><span>{t.opened_at ? timeAgo(t.opened_at) : '—'}</span></div>
                </div>

                <div className="mt-4 flex flex-wrap gap-2">
                  {t.status === 'free' ? (
                    <Button size="sm" onClick={() => openTable(t)}>Abrir</Button>
                  ) : (
                    <>
                      <Button size="sm" variant="secondary" onClick={() => setComanda(t)}>Ver comanda</Button>
                      <Button size="sm" variant="outline" onClick={() => closeTable(t)}>Fechar</Button>
                    </>
                  )}
                  <Button size="sm" variant="ghost" onClick={() => { setEditTable(t); setForm({ number: t.number, seats: t.seats, qty: 1 }); setAddOpen(true); }}>
                    <Pencil className="h-3.5 w-3.5" />
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => deleteTable(t)}><Trash2 className="h-3.5 w-3.5" /></Button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      <Dialog open={addOpen} onOpenChange={setAddOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editTable ? 'Editar mesa' : 'Nova mesa'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-1.5">
              <Label>Número / identificação</Label>
              <Input value={form.number} onChange={(e) => setForm({ ...form, number: e.target.value })} placeholder="01" />
            </div>
            <div className="space-y-1.5">
              <Label>Lugares</Label>
              <Input type="number" min={1} value={form.seats} onChange={(e) => setForm({ ...form, seats: e.target.value })} />
            </div>
            {!editTable && (
              <div className="space-y-1.5">
                <Label>Quantidade (criar várias em sequência)</Label>
                <Input type="number" min={1} value={form.qty} onChange={(e) => setForm({ ...form, qty: e.target.value })} />
                <p className="text-xs text-muted-foreground">Ex.: número 07 e quantidade 5 cria as mesas 07, 08, 09, 10 e 11.</p>
              </div>
            )}
          </div>
          <DialogFooter>
            <DialogClose asChild><Button variant="outline">Cancelar</Button></DialogClose>
            <Button onClick={saveTable}>{editTable ? 'Salvar' : 'Criar mesa'}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={!!comanda} onOpenChange={(o) => !o && setComanda(null)}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Comanda — Mesa {comanda?.number}</DialogTitle>
          </DialogHeader>
          <ComandaBody table={comanda} orders={orders} itemsByOrder={itemsByOrder} currency={restaurant?.currency} tax={restaurant?.service_tax_percent} onChanged={load} />
          <DialogFooter>
            <DialogClose asChild><Button variant="outline">Fechar</Button></DialogClose>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function ComandaBody({ table, orders, itemsByOrder, currency, tax, onChanged }) {
  const order = orders.find((o) => o.id === table?.current_order_id);
  const items = order ? itemsByOrder[order.id] || [] : [];
  const { toast } = useToast();
  const [closing, setClosing] = useState(false);
  const [payMethod, setPayMethod] = useState(order?.payment_method || 'cash');

  if (!order) return <p className="text-sm text-muted-foreground">Sem comanda aberta.</p>;

  const close = async () => {
    setClosing(true);
    await api.Order.update(order.id, { status: 'closed', closed_at: todayISO(), payment_method: payMethod });
    await api.Table.update(table.id, { status: 'free', current_order_id: '', opened_at: '' });
    setClosing(false);
    onChanged();
    toast({ title: 'Comanda fechada', description: `Pago em ${PAYMENTS.find((p) => p.value === payMethod)?.label}` });
  };

  return (
    <div className="space-y-3 py-2">
      {items.length === 0 ? (
        <p className="text-sm text-muted-foreground">Nenhum item adicionado.</p>
      ) : (
        <p className="text-sm text-muted-foreground">Itens carregados do pedido (sem chamada extra)</p>
      )}
      <div className="flex justify-between border-t border-border pt-3 text-sm">
        <span className="text-muted-foreground">Total</span>
        <span className="font-heading text-lg font-semibold">{formatCurrency(order.total, currency)}</span>
      </div>
      <div className="space-y-1.5">
        <Label>Forma de pagamento</Label>
        <Select value={payMethod} onValueChange={setPayMethod}>
          <SelectTrigger><SelectValue /></SelectTrigger>
          <SelectContent>
            {PAYMENTS.map((p) => <SelectItem key={p.value} value={p.value}>{p.label}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>
      <Button onClick={close} disabled={closing} className="w-full">
        {closing ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Fechar comanda'}
      </Button>
    </div>
  );
}