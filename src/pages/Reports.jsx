import React, { useEffect, useState, useMemo } from 'react';
import { api } from '@/lib/restaurant-context';
import { useRestaurant, userRestaurantId } from '@/lib/restaurant-context';
import { formatCurrency, dayKey } from '@/lib/format';
import { Loader2, Download } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useToast } from '@/components/ui/use-toast';

const RANGES = [{ k: '7', l: '7 dias' }, { k: '30', l: '30 dias' }, { k: '90', l: '90 dias' }];

export default function Reports() {
  const { user, restaurant } = useRestaurant();
  const rid = userRestaurantId(user);
  const { toast } = useToast();
  const [range, setRange] = useState('30');
  const [orders, setOrders] = useState([]);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
        const since = new Date(Date.now() - Number(range) * 86400000).toISOString();
        const [o] = await Promise.all([
          api.Order.filter({ restaurant_id: rid, created_date_gte: since }, '-created_date', 500),
        ]);
        setOrders(o);
        // Extract items from orders (OrderRead includes items)
        const allItems = o.flatMap(order => order.items || []);
        setItems(allItems);
        setLoading(false);
      };
  useEffect(() => { if (rid) load(); /* eslint-disable-next-line */ }, [rid, range]);

  const closed = orders.filter((o) => o.status === 'closed');
  const revenue = closed.reduce((s, o) => s + Number(o.total || 0), 0);
  const cancelled = orders.filter((o) => o.status === 'cancelled').length;

  const byDay = useMemo(() => {
    const m = {};
    closed.forEach((o) => { const k = dayKey(o.created_date); m[k] = (m[k] || 0) + Number(o.total || 0); });
    return Object.entries(m).sort((a, b) => a[0].localeCompare(b[0])).map(([d, v]) => ({ d, v }));
  }, [closed]);

  const byProduct = useMemo(() => {
    const m = {};
    items.forEach((i) => {
      if (!m[i.product_name]) m[i.product_name] = { qty: 0, revenue: 0 };
      m[i.product_name].qty += Number(i.quantity || 0);
      m[i.product_name].revenue += Number(i.unit_price || 0) * Number(i.quantity || 0);
    });
    return Object.entries(m).map(([name, v]) => ({ name, ...v })).sort((a, b) => b.revenue - a.revenue);
  }, [items]);

  const byTable = useMemo(() => {
    const m = {};
    closed.forEach((o) => { m[o.table_number] = (m[o.table_number] || 0) + Number(o.total || 0); });
    return Object.entries(m).map(([t, v]) => ({ t, v })).sort((a, b) => b.v - a.v);
  }, [closed]);

  const exportCsv = () => {
    const rows = [['dia', 'faturamento'], ...byDay.map((r) => [r.d, r.v])];
    const csv = rows.map((r) => r.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = 'relatorio-faturamento.csv'; a.click();
    URL.revokeObjectURL(url);
    toast({ title: 'CSV exportado' });
  };

  if (loading) return <div className="grid h-full place-items-center"><Loader2 className="h-7 w-7 animate-spin text-primary" /></div>;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-heading text-3xl font-semibold">Relatórios</h1>
          <p className="text-sm text-muted-foreground">Desempenho do período selecionado.</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex gap-1 rounded-xl border border-border bg-card p-1">
            {RANGES.map((r) => (
              <button key={r.k} onClick={() => setRange(r.k)} className={`rounded-lg px-3 py-1.5 text-sm font-medium ${range === r.k ? 'bg-primary text-primary-foreground' : 'text-muted-foreground'}`}>{r.l}</button>
            ))}
          </div>
          <Button variant="outline" onClick={exportCsv}><Download className="h-4 w-4" /> CSV</Button>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card label="Faturamento" value={formatCurrency(revenue, restaurant?.currency)} />
        <Card label="Pedidos fechados" value={closed.length} />
        <Card label="Ticket médio" value={formatCurrency(closed.length ? revenue / closed.length : 0, restaurant?.currency)} />
        <Card label="Cancelamentos" value={cancelled} />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Section title="Faturamento por dia">
          {byDay.length === 0 ? <Empty /> : byDay.map((r) => (
            <div key={r.d} className="flex items-center justify-between border-b border-border py-2 text-sm last:border-0">
              <span className="text-muted-foreground">{r.d}</span><span className="font-medium">{formatCurrency(r.v, restaurant?.currency)}</span>
            </div>
          ))}
        </Section>
        <Section title="Produtos mais vendidos">
          {byProduct.length === 0 ? <Empty /> : byProduct.slice(0, 8).map((r) => (
            <div key={r.name} className="flex items-center justify-between border-b border-border py-2 text-sm last:border-0">
              <span className="truncate pr-2">{r.name}</span>
              <span className="whitespace-nowrap"><span className="text-muted-foreground">{r.qty}x</span> · <span className="font-medium">{formatCurrency(r.revenue, restaurant?.currency)}</span></span>
            </div>
          ))}
        </Section>
        <Section title="Mesas com maior consumo">
          {byTable.length === 0 ? <Empty /> : byTable.slice(0, 8).map((r) => (
            <div key={r.t} className="flex items-center justify-between border-b border-border py-2 text-sm last:border-0">
              <span>Mesa {r.t}</span><span className="font-medium">{formatCurrency(r.v, restaurant?.currency)}</span>
            </div>
          ))}
        </Section>
        <Section title="Horários de pico">
          <PeakHours orders={orders} />
        </Section>
      </div>
    </div>
  );
}

function PeakHours({ orders }) {
  const hours = useMemo(() => {
    const m = new Array(24).fill(0);
    orders.forEach((o) => { m[new Date(o.created_date).getHours()]++; });
    return m;
  }, [orders]);
  const max = Math.max(1, ...hours);
  return (
    <div className="flex items-end gap-1 pt-2" style={{ height: 140 }}>
      {hours.map((c, h) => (
        <div key={h} className="flex flex-1 flex-col items-center justify-end gap-1">
          <div className="w-full rounded-t bg-primary/70" style={{ height: `${(c / max) * 100}%`, minHeight: c ? 4 : 0 }} />
          {h % 3 === 0 && <span className="text-[10px] text-muted-foreground">{h}h</span>}
        </div>
      ))}
    </div>
  );
}

function Card({ label, value }) {
  return <div className="surface-card p-5"><p className="text-xs uppercase tracking-wider text-muted-foreground">{label}</p><p className="mt-2 font-heading text-2xl font-semibold">{value}</p></div>;
}
function Section({ title, children }) {
  return <div className="surface-card p-5"><h2 className="mb-3 font-heading text-lg font-semibold">{title}</h2>{children}</div>;
}
function Empty() { return <div className="grid h-32 place-items-center text-sm text-muted-foreground">Sem dados no período.</div>; }