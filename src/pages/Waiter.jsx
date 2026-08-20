import React, { useEffect, useState } from 'react';
import { api } from '@/lib/restaurant-context';
import { useRestaurant, userRestaurantId } from '@/lib/restaurant-context';
import { formatCurrency, timeAgo } from '@/lib/format';
import { refreshOrderTotals } from '@/lib/orders';
import { Plus, Loader2, Bell, ClipboardList, LayoutGrid, Check, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogClose
} from '@/components/ui/dialog';
import { useToast } from '@/components/ui/use-toast';

export default function Waiter() {
  return (
    <Tabs defaultValue="tables" className="space-y-6">
      <div>
        <h1 className="font-heading text-3xl font-semibold">Garçom</h1>
        <p className="text-sm text-muted-foreground">Mesas, chamados e pedidos em um só lugar.</p>
      </div>
      <TabsList>
        <TabsTrigger value="tables"><LayoutGrid className="mr-1.5 h-4 w-4" /> Mesas</TabsTrigger>
        <TabsTrigger value="calls"><Bell className="mr-1.5 h-4 w-4" /> Chamados</TabsTrigger>
        <TabsTrigger value="orders"><ClipboardList className="mr-1.5 h-4 w-4" /> Pedidos</TabsTrigger>
      </TabsList>
      <TabsContent value="tables"><WaiterTables /></TabsContent>
      <TabsContent value="calls"><Calls /></TabsContent>
      <TabsContent value="orders"><ActiveOrders /></TabsContent>
    </Tabs>
  );
}

function WaiterTables() {
  const { user, restaurant } = useRestaurant();
  const rid = userRestaurantId(user);
  const { toast } = useToast();
  const [tables, setTables] = useState([]);
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [adding, setAdding] = useState(null);
  const [search, setSearch] = useState('');

  const load = async () => {
    const [t, o] = await Promise.all([
      api.Table.filter({ restaurant_id: rid }, 'number', 500),
      api.Order.filter({ restaurant_id: rid, status: { $in: ['received', 'preparing', 'ready', 'delivered'] } }, '-created_date', 500),
    ]);
    setTables(t); setOrders(o); setLoading(false);
  };
  useEffect(() => { if (rid) load(); /* eslint-disable-next-line */ }, [rid]);

  const openTable = async (t) => {
    // Backend `OrderCreate` requires `items`. Passing an empty array opens the
    // table without products; the OrderService also flips the table to
    // `occupied` and sets `current_order_id` in the same transaction, so
    // there is no need to update the table afterwards.
    const order = await api.Order.create({
      table_id: t.id,
      table_number: t.number,
      items: [],
    });
    toast({ title: `Mesa ${t.number} aberta` });
    load();
  };

  const filtered = tables.filter((t) => t.number.toLowerCase().includes(search.toLowerCase()));

  if (loading) return <div className="grid h-full place-items-center"><Loader2 className="h-7 w-7 animate-spin text-primary" /></div>;

  return (
    <div className="space-y-4">
      <Input placeholder="Buscar mesa..." value={search} onChange={(e) => setSearch(e.target.value)} className="max-w-xs" />
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {filtered.map((t) => {
          const order = orders.find((o) => o.id === t.current_order_id);
          return (
            <div key={t.id} className="surface-card p-4">
              <div className="flex items-center justify-between">
                <span className="font-heading text-lg font-semibold">Mesa {t.number}</span>
                <span className={`rounded-full px-2 py-0.5 text-xs ${t.status === 'free' ? 'bg-success/15 text-success' : 'bg-primary/15 text-primary'}`}>
                  {t.status === 'free' ? 'Livre' : 'Ocupada'}
                </span>
              </div>
              {order && <p className="mt-1 text-sm text-muted-foreground">{formatCurrency(order.total, restaurant?.currency)} · {timeAgo(t.opened_at)}</p>}
              <div className="mt-3 flex gap-2">
                {t.status === 'free'
                  ? <Button size="sm" onClick={() => openTable(t)}>Abrir</Button>
                  : <Button size="sm" variant="secondary" onClick={() => setAdding(t)}>Adicionar item</Button>}
              </div>
            </div>
          );
        })}
      </div>

      <AddItemDialog table={adding} orders={orders} restaurant={restaurant} onClose={() => setAdding(null)} onChanged={load} />
    </div>
  );
}

function AddItemDialog({ table, orders, restaurant, onClose, onChanged }) {
  const rid = userRestaurantId(useRestaurant().user);
  const { toast } = useToast();
  const [products, setProducts] = useState([]);
  const [items, setItems] = useState([]);
  const [qty, setQty] = useState({});
  const [notes, setNotes] = useState({});
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!table) return;
    api.Product.filter({ restaurant_id: rid, available: true }, '-created_date', 500).then(setProducts);
  }, [table, rid]);

  const order = orders.find((o) => o.id === table?.current_order_id);
  useEffect(() => { if (order) api.OrderItem.filter({ order_id: order.id }).then(setItems); }, [order]);

  if (!table || !order) return null;

  const add = async (p) => {
    const q = qty[p.id] || 1;
    setSaving(true);
    await api.OrderItem.create({
      restaurant_id: rid, order_id: order.id, product_id: p.id, product_name: p.name,
      quantity: Number(q), unit_price: Number(p.price), notes: notes[p.id] || '',
    });
    await refreshOrderTotals(order.id, restaurant?.service_tax_percent);
    const it = await api.OrderItem.filter({ order_id: order.id });
    setItems(it);
    setQty({ ...qty, [p.id]: 1 }); setNotes({ ...notes, [p.id]: '' });
    setSaving(false);
    toast({ title: `${q}x ${p.name} adicionado` });
  };

  return (
    <Dialog open={!!table} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-lg">
        <DialogHeader><DialogTitle>Adicionar — Mesa {table.number}</DialogTitle></DialogHeader>
        <div className="max-h-[60vh] space-y-2 overflow-y-auto py-2">
          {products.map((p) => (
            <div key={p.id} className="rounded-xl border border-border bg-secondary/30 p-3">
              <div className="flex items-center justify-between">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">{p.name}</p>
                  <p className="text-xs text-muted-foreground">{formatCurrency(p.price, restaurant?.currency)}</p>
                </div>
                <div className="flex items-center gap-2">
                  <input type="number" min={1} value={qty[p.id] || 1} onChange={(e) => setQty({ ...qty, [p.id]: e.target.value })} className="w-14 rounded-lg border border-border bg-background px-2 py-1 text-sm" />
                  <Button size="sm" disabled={saving} onClick={() => add(p)}><Plus className="h-3.5 w-3.5" /></Button>
                </div>
              </div>
              <input value={notes[p.id] || ''} onChange={(e) => setNotes({ ...notes, [p.id]: e.target.value })} placeholder="Observação (ex: sem cebola)" className="mt-2 w-full rounded-lg border border-border bg-background px-2 py-1 text-xs" />
            </div>
          ))}
        </div>
        <div className="rounded-xl border border-border p-3">
          <p className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">Itens da comanda</p>
          {items.length === 0 ? <p className="text-sm text-muted-foreground">Nenhum item ainda.</p> : items.map((it) => (
            <div key={it.id} className="flex justify-between text-sm"><span>{it.quantity}x {it.product_name}</span><span>{formatCurrency(it.unit_price * it.quantity, restaurant?.currency)}</span></div>
          ))}
        </div>
        <DialogFooter>
          <DialogClose asChild><Button variant="outline" onClick={onChanged}>Concluir</Button></DialogClose>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function Calls() {
  const { user } = useRestaurant();
  const rid = userRestaurantId(user);
  const { toast } = useToast();
  const [calls, setCalls] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setCalls(await api.ServiceCall.filter({ restaurant_id: rid, status: 'pending' }, '-created_date', 200));
    setLoading(false);
  };
  useEffect(() => { if (rid) load(); /* eslint-disable-next-line */ }, [rid]);
  useEffect(() => {
    if (!rid) return;
    const unsub = api.ServiceCall.subscribe(() => load());
    return unsub;
    /* eslint-disable-next-line */
  }, [rid]);

  const assume = async (c) => { await api.ServiceCall.update(c.id, { status: 'assumed' }); toast({ title: `Chamado da Mesa ${c.table_number} assumido` }); load(); };
  const resolve = async (c) => { await api.ServiceCall.update(c.id, { status: 'resolved' }); load(); };

  const label = { help: 'Preciso de ajuda', order: 'Quero fazer pedido', bill: 'Quero a conta', other: 'Outro' };

  if (loading) return <div className="grid h-full place-items-center"><Loader2 className="h-7 w-7 animate-spin text-primary" /></div>;
  return (
    <div className="space-y-3">
      {calls.length === 0 ? <div className="surface-card grid h-40 place-items-center text-sm text-muted-foreground">Nenhum chamado pendente.</div> : calls.map((c) => (
        <div key={c.id} className="surface-card flex items-center justify-between p-4">
          <div className="flex items-center gap-3">
            <div className="grid h-10 w-10 place-items-center rounded-xl bg-destructive/15 text-destructive"><Bell className="h-5 w-5" /></div>
            <div>
              <p className="font-medium">Mesa {c.table_number}</p>
              <p className="text-sm text-muted-foreground">{label[c.type]}</p>
            </div>
          </div>
          <div className="flex gap-2">
            <Button size="sm" variant="secondary" onClick={() => assume(c)}>Assumir</Button>
            <Button size="sm" variant="ghost" onClick={() => resolve(c)}><Check className="h-4 w-4" /></Button>
          </div>
        </div>
      ))}
    </div>
  );
}

function ActiveOrders() {
  const { user, restaurant } = useRestaurant();
  const rid = userRestaurantId(user);
  const { toast } = useToast();
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setOrders(await api.Order.filter({ restaurant_id: rid, status: { $in: ['received', 'preparing', 'ready', 'delivered'] } }, '-created_date', 200));
    setLoading(false);
  };
  useEffect(() => { if (rid) load(); /* eslint-disable-next-line */ }, [rid]);

  const advance = async (o, status, msg) => { await api.Order.update(o.id, { status }); toast({ title: msg }); load(); };
  const statusLabel = { received: 'Recebido', preparing: 'Em preparo', ready: 'Pronto', delivered: 'Entregue' };

  if (loading) return <div className="grid h-full place-items-center"><Loader2 className="h-7 w-7 animate-spin text-primary" /></div>;
  return (
    <div className="space-y-3">
      {orders.length === 0 ? <div className="surface-card grid h-40 place-items-center text-sm text-muted-foreground">Nenhum pedido ativo.</div> : orders.map((o) => (
        <div key={o.id} className="surface-card flex flex-wrap items-center justify-between gap-3 p-4">
          <div>
            <p className="font-medium">Mesa {o.table_number} · {formatCurrency(o.total, restaurant?.currency)}</p>
            <p className="text-sm text-muted-foreground">{statusLabel[o.status]} · {timeAgo(o.created_date)}</p>
          </div>
          <div className="flex gap-2">
            {o.status === 'received' && <Button size="sm" onClick={() => advance(o, 'preparing', 'Preparo iniciado')}>Iniciar</Button>}
            {o.status === 'preparing' && <Button size="sm" variant="secondary" onClick={() => advance(o, 'ready', 'Pedido pronto')}>Pronto</Button>}
            {o.status === 'ready' && <Button size="sm" variant="secondary" onClick={() => advance(o, 'delivered', 'Entregue')}>Entregue</Button>}
          </div>
        </div>
      ))}
    </div>
  );
}