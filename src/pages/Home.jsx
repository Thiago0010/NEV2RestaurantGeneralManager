import React, { useEffect, useState, useMemo } from 'react';
import { api } from '@/lib/restaurant-context';
import { useRestaurant, userRestaurantId } from '@/lib/restaurant-context';
import { formatCurrency, isToday, dayKey, safeNumber } from '@/lib/format';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid
} from 'recharts';
import { DollarSign, ShoppingBag, TrendingUp, Utensils, Clock, Bell, Loader2, Flame } from 'lucide-react';
import Footer from '@/components/Footer';

const RANGES = [
  { key: 'today', label: 'Hoje' },
  { key: '7', label: '7 dias' },
  { key: '30', label: '30 dias' },
];

function StatCard({ icon: Icon, label, value, sub, accent }) {
  return (
    <div className="surface-card p-5">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs uppercase tracking-wider text-muted-foreground">{label}</p>
          <p className="mt-2 font-heading text-2xl font-semibold">{value}</p>
          {sub && <p className="mt-1 text-xs text-muted-foreground">{sub}</p>}
        </div>
        <div className={`grid h-10 w-10 place-items-center rounded-xl ${accent}`}>
          <Icon className="h-5 w-5" />
        </div>
      </div>
    </div>
  );
}

export default function Home() {
  const { user, restaurant } = useRestaurant();
  const rid = userRestaurantId(user);
  const [range, setRange] = useState('today');
  const [orders, setOrders] = useState([]);
  const [tables, setTables] = useState([]);
  const [calls, setCalls] = useState([]);
  const [revenueStats, setRevenueStats] = useState({ total_revenue: 0, order_count: 0 });
  const [topProductsStats, setTopProductsStats] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = async () => {
      if (!rid) { setLoading(false); return; }

      setLoading(true);
      setError(null);
      try {
        // Fetch 30 days to ensure we have all orders that could be closed today
        const since = new Date(Date.now() - 30 * 86400000).toISOString();

        const [o, t, c, rs, tp] = await Promise.allSettled([
          api.Order.filter({
            restaurant_id: rid,
            created_date_gte: since
          }, '-created_date', 500),
          api.Table.filter({ restaurant_id: rid }, '-created_date', 500),
          api.ServiceCall.filter({ restaurant_id: rid, status: 'pending' }, '-created_date', 200),
          api.analytics.getRevenue({ since }),
          api.analytics.getTopProducts(),
        ]);

        setOrders(o.status === 'fulfilled' ? o.value : []);
        setTables(t.status === 'fulfilled' ? t.value : []);
        setCalls(c.status === 'fulfilled' ? c.value : []);
        setRevenueStats(rs.status === 'fulfilled' ? rs.value : { total_revenue: 0, order_count: 0 });
        setTopProductsStats(tp.status === 'fulfilled' ? tp.value : []);
      } catch (err) {
        setError(err.message || 'Erro ao carregar dashboard');
        setOrders([]); setTables([]); setCalls([]);
      } finally {
        setLoading(false);
      }
    };

  useEffect(() => { if (rid) load(); }, [rid, range]);

  const filtered = useMemo(() => {
    if (range !== 'today') return orders;
    return orders.filter((o) => isToday(o.created_date));
  }, [orders, range]);

  const closed = useMemo(() => {
    return orders.filter((o) => o.status === 'closed');
  }, [orders]);

  const revenueToday = useMemo(() => {
    return closed
      .filter((o) => isToday(o.closed_at))
      .reduce((s, o) => s + safeNumber(o.total), 0);
  }, [closed]);

  const ticket = useMemo(() => {
    const count = closed.filter((o) => isToday(o.closed_at)).length;
    return count ? revenueToday / count : 0;
  }, [closed, revenueToday]);

  const occupied = tables.filter((t) => t.status !== 'free').length;
  const free = tables.filter((t) => t.status === 'free').length;
  const preparing = orders.filter((o) => ['received', 'preparing'].includes(o.status) && isToday(o.created_date)).length;

  const byDay = useMemo(() => {
    const map = {};
    closed.forEach((o) => {
      const k = dayKey(o.closed_at || o.created_date);
      const val = safeNumber(o.total);
      map[k] = (map[k] || 0) + val;
    });
    return Object.entries(map).map(([k, v]) => ({ day: k, value: +v.toFixed(2) }));
  }, [closed]);

  const topProducts = topProductsStats;

  if (loading) return <div className="grid h-full place-items-center"><Loader2 className="h-7 w-7 animate-spin text-primary" /></div>;
  if (error) return <div className="p-4 text-destructive text-center">{error}</div>;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-heading text-3xl font-semibold">Dashboard</h1>
          <p className="text-sm text-muted-foreground">Como está {restaurant?.name || 'seu restaurante'} agora.</p>
        </div>
        <div className="flex gap-1 rounded-xl border border-border bg-card p-1">
          {RANGES.map((r) => (
            <button key={r.key} onClick={() => setRange(r.key)}
              className={`rounded-lg px-3 py-1.5 text-sm font-medium transition ${range === r.key ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground'}`}
            >
              {r.label}
            </button>
          ))}
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard icon={DollarSign} label="Faturamento" value={formatCurrency(revenueToday, restaurant?.currency)} accent="bg-primary/15 text-primary" />
        <StatCard icon={ShoppingBag} label="Pedidos" value={filtered.length} sub={`${closed.length} fechados`} accent="bg-accent/15 text-accent-foreground" />
        <StatCard icon={TrendingUp} label="Ticket médio" value={formatCurrency(ticket, restaurant?.currency)} accent="bg-success/15 text-success" />
        <StatCard icon={Clock} label="Em preparo" value={preparing} accent="bg-warning/15 text-warning" />
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard icon={Utensils} label="Mesas ocupadas" value={occupied} sub={`${free} livres`} accent="bg-primary/15 text-primary" />
        <StatCard icon={Utensils} label="Mesas livres" value={free} accent="bg-secondary text-secondary-foreground" />
        <StatCard icon={Bell} label="Chamados pendentes" value={calls.length} accent="bg-destructive/15 text-destructive" />
        <StatCard icon={Flame} label="Taxa de serviço" value={`${restaurant?.service_tax_percent ?? 0}%`} accent="bg-accent/15 text-accent-foreground" />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="surface-card p-5">
          <h2 className="font-heading text-lg font-semibold">Faturamento por dia</h2>
          <p className="mb-4 text-xs text-muted-foreground">Total fechado por dia</p>
          {byDay.length === 0 ? (
            <EmptyState text="Sem faturamento no período." />
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={byDay} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
                <XAxis dataKey="day" stroke="hsl(var(--muted-foreground))" fontSize={12} tickLine={false} axisLine={false} />
                <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} tickLine={false} axisLine={false} />
                <Tooltip cursor={{ fill: 'hsl(var(--muted) / 0.4)' }} contentStyle={{ background: 'hsl(var(--popover))', border: '1px solid hsl(var(--border))', borderRadius: 12, color: 'hsl(var(--foreground))' }} formatter={(v) => formatCurrency(v, restaurant?.currency)} />
                <Bar dataKey="value" radius={[6, 6, 0, 0]} fill="hsl(var(--primary))" />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="surface-card p-5">
          <h2 className="font-heading text-lg font-semibold">Produtos mais vendidos</h2>
          <p className="mb-4 text-xs text-muted-foreground">Por quantidade no período</p>
          {topProducts.length === 0 ? (
            <EmptyState text="Sem vendas no período." />
          ) : (
            <div className="space-y-3">
              {topProducts.map((p, i) => (
                <div key={p.name} className="flex items-center gap-3">
                  <span className="grid h-7 w-7 place-items-center rounded-lg bg-secondary text-xs font-semibold text-secondary-foreground">{i + 1}</span>
                  <span className="flex-1 truncate text-sm">{p.name}</span>
                  <div className="h-1.5 w-24 overflow-hidden rounded-full bg-secondary">
                    <div className="h-full rounded-full bg-primary" style={{ width: `${(p.qty / topProducts[0].qty) * 100}%` }} />
                  </div>
                  <span className="w-8 text-right text-sm font-medium">{p.qty}x</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
      <Footer />
    </div>
  );
}

function EmptyState({ text }) {
  return <div className="grid h-40 place-items-center text-sm text-muted-foreground">{text}</div>;
}