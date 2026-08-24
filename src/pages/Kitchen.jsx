import React, { useEffect, useState, useRef } from 'react';
import { api } from '@/lib/restaurant-context';
import { useRestaurant, userRestaurantId } from '@/lib/restaurant-context';
import { timeAgo } from '@/lib/format';
import { Loader2, Check, Flame } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useToast } from '@/components/ui/use-toast';

const COLUMNS = [
  { key: 'received', label: 'Novos', accent: 'border-l-primary' },
  { key: 'preparing', label: 'Em preparo', accent: 'border-l-accent' },
  { key: 'ready', label: 'Prontos', accent: 'border-l-success' },
];

export default function Kitchen() {
  const { user, restaurant } = useRestaurant();
  const rid = userRestaurantId(user);
  const { toast } = useToast();
  const [orders, setOrders] = useState([]);
  const [itemsMap, setItemsMap] = useState({});
  const [loading, setLoading] = useState(true);
  const seenIds = useRef(new Set());

  const load = async () => {
      const o = await api.Order.filter(
        { restaurant_id: rid, status: { $in: ['received', 'preparing', 'ready'] } },
        'created_date', 500
      );
      // alert on new received orders
      o.forEach((ord) => {
        if (ord.status === 'received' && !seenIds.current.has(ord.id)) {
          if (seenIds.current.size > 0) toast({ title: `Novo pedido · Mesa ${ord.table_number}`, description: 'Pedido recebido na cozinha.' });
          seenIds.current.add(ord.id);
        }
      });
      // forget ids no longer active
      const active = new Set(o.map((x) => x.id));
      seenIds.current.forEach((id) => { if (!active.has(id)) seenIds.current.delete(id); });
      setOrders(o);
      const map = {};
      await Promise.all(o.map(async (ord) => { map[ord.id] = await api.OrderItem.filter({ order_id: ord.id }); }));
      setItemsMap(map);
      setLoading(false);
    };

    useEffect(() => { if (rid) load();   }, [rid]);
    useEffect(() => {
      if (!rid) return;
      const unsub = api.Order.subscribe(() => load());
      return unsub;
       
    }, [rid]);

    const setStatus = async (order, status, msg) => {
      await api.Order.update(order.id, { status });
      toast({ title: msg });
      load();
    };

  if (loading) return <div className="grid h-full place-items-center"><Loader2 className="h-7 w-7 animate-spin text-primary" /></div>;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-heading text-3xl font-semibold">Cozinha</h1>
        <p className="text-sm text-muted-foreground">Kanban de pedidos em tempo real.</p>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        {COLUMNS.map((col) => {
          const list = orders.filter((o) => o.status === col.key);
          return (
            <div key={col.key} className="surface-card flex flex-col p-4">
              <div className="mb-3 flex items-center justify-between">
                <h2 className="font-heading text-lg font-semibold">{col.label}</h2>
                <span className="rounded-full bg-secondary px-2.5 py-0.5 text-xs font-medium text-secondary-foreground">{list.length}</span>
              </div>
              <div className="space-y-3">
                {list.length === 0 ? (
                  <div className="grid h-32 place-items-center rounded-xl border border-dashed border-border text-xs text-muted-foreground">Vazio</div>
                ) : list.map((o) => (
                  <div key={o.id} className={`rounded-xl border border-border border-l-4 ${col.accent} bg-secondary/30 p-3 ${o.status === 'received' ? 'animate-pulse-once' : ''}`}>
                    <div className="flex items-center justify-between">
                      <span className="font-heading font-semibold">Mesa {o.table_number}</span>
                      <span className="text-xs text-muted-foreground">{timeAgo(o.created_date)}</span>
                    </div>
                    {o.notes && <p className="mt-1 rounded-lg bg-warning/10 px-2 py-1 text-xs text-warning">⚠ {o.notes}</p>}
                    <div className="mt-2 space-y-1">
                      {(itemsMap[o.id] || []).map((it) => (
                        <div key={it.id} className="text-sm">
                          <span className="font-medium">{it.quantity}x</span> {it.product_name}
                          {it.notes && <p className="pl-5 text-xs text-muted-foreground">{it.notes}</p>}
                        </div>
                      ))}
                    </div>
                    <div className="mt-3 flex gap-2">
                      {o.status === 'received' && <Button size="sm" onClick={() => setStatus(o, 'preparing', 'Preparo iniciado')}><Flame className="h-3.5 w-3.5" /> Iniciar</Button>}
                      {o.status === 'preparing' && <Button size="sm" variant="secondary" onClick={() => setStatus(o, 'ready', 'Pedido pronto')}><Check className="h-3.5 w-3.5" /> Pronto</Button>}
                      {o.status === 'ready' && <Button size="sm" variant="secondary" onClick={() => setStatus(o, 'delivered', 'Pedido entregue')}><Check className="h-3.5 w-3.5" /> Entregue</Button>}
                      <Button size="sm" variant="ghost" onClick={() => setStatus(o, 'cancelled', 'Pedido cancelado')}>Cancelar</Button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}