import React, { useEffect, useState, useMemo, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '@/lib/restaurant-context';
import { publicApi } from '@/api/client';
import { formatCurrency } from '@/lib/format';
import { Flame, Plus, Minus, ShoppingCart, Bell, Check, Loader2, ArrowLeft, Receipt } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useToast } from '@/components/ui/use-toast';

const STEPS = [
  { key: 'received', label: 'Recebido' },
  { key: 'preparing', label: 'Em preparo' },
  { key: 'ready', label: 'Pronto' },
  { key: 'delivered', label: 'Entregue' },
];

export default function CustomerMenu() {
  const { slug, num } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [restaurant, setRestaurant] = useState(null);
  const [categories, setCategories] = useState([]);
  const [products, setProducts] = useState([]);
  const [table, setTable] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeCat, setActiveCat] = useState(null);
  const [cart, setCart] = useState({});
  const [notes, setNotes] = useState({});
  const [sending, setSending] = useState(false);
  const [order, setOrder] = useState(null);
  const [orderItems, setOrderItems] = useState([]);
  const [view, setView] = useState('menu'); // menu | cart | tracking
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setError('');
    try {
      const r = await api.restaurant.getPublic(slug);
      if (!r) { setError('Estabelecimento não encontrado.'); setLoading(false); return; }
      const rest = r;
      setRestaurant(rest);
      const [cats, prods, tableData] = await Promise.all([
        publicApi.getCategories(rest.id),
        publicApi.getProducts(rest.id, null),
        publicApi.getTable(rest.id, num),
      ]);
      setCategories(cats);
      setProducts(prods);
      if (tableData) {
        setTable(tableData);
      } else {
        setError(`Mesa ${num} não encontrada neste estabelecimento.`);
      }
      if (cats.length) setActiveCat(cats[0].id);
    } catch (e) {
      // Native fetch failures (network down, CORS, mixed-content) surface as
      // a TypeError with a generic `message` like "Failed to fetch" or
      // "NetworkError when attempting to fetch resource." Show something
      // actionable instead — most of the time this is the LAN-host case
      // where the API URL was hardcoded to localhost and the request can't
      // reach the backend.
      const raw = e?.message || '';
      const isNetworkFailure = /failed to fetch|networkerror|load failed/i.test(raw);
      if (isNetworkFailure) {
        setError('Não foi possível contactar o servidor. Verifique sua conexão e tente novamente.');
      } else {
        setError(raw || 'Não foi possível carregar o cardápio. Verifique sua conexão.');
      }
    } finally {
      setLoading(false);
    }
  }, [slug, num]);

  useEffect(() => { load(); }, [load]);

  // track open order for this table
    useEffect(() => {
      if (!table) return;
      let active = true;
      const poll = async () => {
        const o = await api.Order.getPublicActive(restaurant?.id, table.id);
        if (!active) return;
        if (o) {
          setOrder(o);
          // `getPublicActive` already returns the order with its items embedded
          // (backend uses selectinload). No second call needed — and the
          // authenticated `GET /orders/{id}` returns 404 for anonymous clients.
          setOrderItems(o.items || []);
        }
      };
      poll();
      const unsub = api.Order.subscribe(poll);
      const t = setInterval(poll, 8000);
      return () => { active = false; unsub(); clearInterval(t); };
    }, [table, restaurant]);

  const cartList = useMemo(() => Object.entries(cart).map(([pid, q]) => {
    const p = products.find((x) => x.id === pid);
    return p ? { ...p, qty: q, note: notes[pid] || '' } : null;
  }).filter(Boolean), [cart, products, notes]);

  const cartTotal = useMemo(() => cartList.reduce((s, i) => s + i.price * i.qty, 0), [cartList]);
  const cartCount = useMemo(() => cartList.reduce((s, i) => s + i.qty, 0), [cartList]);

  const setQty = (pid, delta) => setCart((c) => {
    const q = (c[pid] || 0) + delta;
    const next = { ...c };
    if (q <= 0) delete next[pid]; else next[pid] = q;
    return next;
  });

  const sendOrder = async () => {
        if (!table || !restaurant || cartList.length === 0) return;
        setSending(true);
        try {
          const tax = restaurant.service_tax_percent || 0;
          const itemsPayload = cartList.map((i) => ({
            product_id: i.id,
            product_name: i.name,
            quantity: i.qty,
            unit_price: i.price,
            notes: i.note,
          }));
          let orderId = table.current_order_id;
          try {
            if (orderId) {
              // append to existing open order using public endpoint
              await api.Order.addItemsPublic(restaurant.id, orderId, itemsPayload);
            } else {
              // create order with items in one shot using public endpoint
              const o = await api.Order.createPublic(restaurant.id, {
                table_id: table.id,
                table_number: table.number,
                items: itemsPayload,
              });
              orderId = o.id;
            }
          } catch (e) {
            // The backend returns 409 when the table already has an open
            // order — happens when the cached `current_order_id` is stale
            // (e.g. the kitchen marked the previous order as delivered
            // but the client never refreshed). Recover by fetching the
            // active order and adding the cart to that one instead.
            const isConflict = e?.status === 409 || /open order/i.test(e?.message || '');
            if (isConflict) {
              const active = await api.Order.getPublicActive(restaurant.id, table.id);
              if (active?.id) {
                orderId = active.id;
                await api.Order.addItemsPublic(restaurant.id, orderId, itemsPayload);
              } else {
                throw e;
              }
            } else {
              throw e;
            }
          }
          const updated = await api.Order.getPublicActive(restaurant.id, table.id);
          setOrder(updated);
          setOrderItems(updated?.items || []);
          setCart({}); setNotes({});
          setView('tracking');
          toast({ title: 'Pedido enviado!', description: `Mesa ${table.number}` });
        } catch (e) {
          toast({ title: 'Não foi possível enviar o pedido', description: e?.message, variant: 'destructive' });
        } finally {
          setSending(false);
        }
      };

  const callWaiter = async (type) => {
        try {
          await api.ServiceCall.createPublic(restaurant.id, { table_id: table.id, table_number: table.number, type });
          const label = type === 'help' ? 'Ajuda' : type === 'bill' ? 'Conta' : 'Pedido';
          toast({ title: `Chamado enviado: ${label}`, description: `Mesa ${table.number} · aguarde o garçom.` });
        } catch (e) {
          toast({ title: 'Não foi possível chamar o garçom', description: e?.message, variant: 'destructive' });
        }
      };

  if (loading) return <div className="grid min-h-screen place-items-center bg-background"><Loader2 className="h-7 w-7 animate-spin text-primary" /></div>;
  if (error) return (
    <div className="grid min-h-screen place-items-center bg-background p-6 text-center">
      <div>
        <p className="font-heading text-xl font-semibold">{error}</p>
        <Button variant="link" onClick={() => navigate('/')}>Voltar ao painel</Button>
      </div>
    </div>
  );

  const accent = restaurant.accent_color || '#e07a3c';

  if (view === 'tracking' && order) {
    const stepIdx = STEPS.findIndex((s) => s.key === order.status);
    return (
      <div className="min-h-screen bg-background">
        <Header restaurant={restaurant} tableNumber={table.number} onBack={() => setView('menu')} onCallWaiter={callWaiter} />
        <div className="mx-auto max-w-lg space-y-6 p-4">
          <div className="surface-card p-6 text-center">
            <div className="mx-auto grid h-14 w-14 place-items-center rounded-full bg-success/15"><Check className="h-7 w-7 text-success" /></div>
            <h2 className="mt-3 font-heading text-2xl font-semibold">Pedido enviado</h2>
            <p className="text-sm text-muted-foreground">Acompanhe o preparo abaixo.</p>
          </div>

          <div className="surface-card p-5">
            <div className="flex items-center justify-between">
              {STEPS.map((s, i) => (
                <div key={s.key} className="flex flex-1 flex-col items-center">
                  <div className={`grid h-9 w-9 place-items-center rounded-full border-2 text-sm font-semibold ${i <= stepIdx ? 'border-transparent text-white' : 'border-border text-muted-foreground'}`} style={i <= stepIdx ? { background: accent } : {}}>{i <= stepIdx ? <Check className="h-4 w-4" /> : i + 1}</div>
                  <span className="mt-2 text-xs text-muted-foreground">{s.label}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="surface-card p-5">
            <h3 className="mb-3 font-heading text-lg font-semibold">Seu pedido</h3>
            {orderItems.map((it) => (
              <div key={it.id} className="flex justify-between border-b border-border py-2 text-sm last:border-0">
                <span>{it.quantity}x {it.product_name}{it.notes && <span className="block text-xs text-muted-foreground">{it.notes}</span>}</span>
                <span>{formatCurrency(it.unit_price * it.quantity, restaurant.currency)}</span>
              </div>
            ))}
            <div className="mt-3 flex justify-between font-semibold"><span>Total</span><span>{formatCurrency(order.total, restaurant.currency)}</span></div>
          </div>

          <div className="grid grid-cols-3 gap-2">
            <Button variant="secondary" onClick={() => callWaiter('help')}><Bell className="h-4 w-4" /> Ajuda</Button>
            <Button variant="secondary" onClick={() => callWaiter('order')}><Plus className="h-4 w-4" /> Pedir</Button>
            <Button variant="secondary" onClick={() => callWaiter('bill')}><Receipt className="h-4 w-4" /> Conta</Button>
          </div>
          <Button variant="outline" className="w-full" onClick={() => setView('menu')}><ArrowLeft className="mr-2 h-4 w-4" /> Voltar ao cardápio</Button>
        </div>
      </div>
    );
  }

  const catProducts = products.filter((p) => p.category_id === activeCat);

  return (
    <div className="min-h-screen bg-background">
      <Header restaurant={restaurant} tableNumber={table.number} onBack={() => navigate('/')} />
      <div className="mx-auto max-w-3xl p-4 pb-28">
        <div className="surface-card mb-4 flex items-center justify-between gap-3 p-4">
          <div>
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Você está na</p>
            <p className="font-heading text-2xl font-semibold" style={{ color: accent }}>
              Mesa {table.number}
            </p>
          </div>
          <Button size="sm" variant="outline" onClick={() => callWaiter('help')}>
            <Bell className="h-4 w-4" /> Chamar garçom
          </Button>
        </div>
        {restaurant.welcome_message && (
          <div className="surface-card mb-4 p-5" style={{ borderColor: `${accent}40` }}>
            <p className="text-sm" style={{ color: accent }}>{restaurant.welcome_message}</p>
          </div>
        )}

        <div className="sticky top-0 z-10 -mx-4 mb-4 flex gap-2 overflow-x-auto bg-background/90 px-4 py-2 backdrop-blur">
          {categories.map((c) => (
            <button key={c.id} onClick={() => setActiveCat(c.id)}
              className={`whitespace-nowrap rounded-full border px-4 py-2 text-sm font-medium transition ${activeCat === c.id ? 'border-transparent text-white' : 'border-border text-muted-foreground'}`}
              style={activeCat === c.id ? { background: accent } : {}}>
              {c.name}
            </button>
          ))}
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          {catProducts.length === 0 ? (
            <p className="col-span-full py-10 text-center text-sm text-muted-foreground">Nenhum produto disponível nesta categoria.</p>
          ) : catProducts.map((p) => (
            <div key={p.id} className="surface-card overflow-hidden">
              <div className="relative h-36 bg-secondary">
                {p.image_url ? <img src={p.image_url} alt={p.name} className="h-full w-full object-cover" /> : <div className="grid h-full place-items-center"><Flame className="h-8 w-8 text-muted-foreground" /></div>}
                {p.featured && <span className="absolute left-2 top-2 rounded-full px-2 py-0.5 text-xs font-medium text-white" style={{ background: accent }}>Destaque</span>}
              </div>
              <div className="p-4">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="truncate font-medium">{p.name}</p>
                    <p className="font-heading font-semibold" style={{ color: accent }}>{formatCurrency(p.price, restaurant.currency)}</p>
                  </div>
                </div>
                {p.description && <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">{p.description}</p>}
                {cart[p.id] ? (
                  <div className="mt-3 flex items-center gap-2">
                    <button onClick={() => setQty(p.id, -1)} className="grid h-8 w-8 place-items-center rounded-lg border border-border"><Minus className="h-4 w-4" /></button>
                    <span className="w-8 text-center font-medium">{cart[p.id]}</span>
                    <button onClick={() => setQty(p.id, 1)} className="grid h-8 w-8 place-items-center rounded-lg text-white" style={{ background: accent }}><Plus className="h-4 w-4" /></button>
                    <input value={notes[p.id] || ''} onChange={(e) => setNotes({ ...notes, [p.id]: e.target.value })} placeholder="obs" className="ml-1 flex-1 rounded-lg border border-border bg-background px-2 py-1 text-xs" />
                  </div>
                ) : (
                  <Button className="mt-3 w-full" variant="secondary" onClick={() => setQty(p.id, 1)}><Plus className="h-4 w-4" /> Adicionar</Button>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {cartCount > 0 && (
        <div className="fixed inset-x-0 bottom-0 z-20 border-t border-border bg-card/95 p-4 backdrop-blur">
          <div className="mx-auto flex max-w-3xl items-center justify-between gap-3">
            <div>
              <p className="text-xs text-muted-foreground">{cartCount} {cartCount === 1 ? 'item' : 'itens'}</p>
              <p className="font-heading text-lg font-semibold">{formatCurrency(cartTotal, restaurant.currency)}</p>
            </div>
            <Button onClick={() => setView('cart')} size="lg"><ShoppingCart className="h-4 w-4" /> Revisar pedido</Button>
          </div>
        </div>
      )}

      {/* Cart review sheet */}
      {view === 'cart' && (
        <div className="fixed inset-0 z-30 flex items-end justify-center bg-black/60 p-0 sm:items-center sm:p-6" onClick={() => setView('menu')}>
          <div className="w-full max-w-lg surface-card rounded-t-2xl p-5 sm:rounded-2xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between">
              <h2 className="font-heading text-xl font-semibold">Seu pedido · Mesa {table.number}</h2>
              <button onClick={() => setView('menu')} className="text-muted-foreground">✕</button>
            </div>
            <div className="mt-4 max-h-[50vh] space-y-3 overflow-y-auto">
              {cartList.length === 0 ? <p className="text-sm text-muted-foreground">Carrinho vazio.</p> : cartList.map((i) => (
                <div key={i.id} className="flex items-start justify-between gap-3 border-b border-border pb-3">
                  <div className="flex-1">
                    <p className="text-sm font-medium">{i.qty}x {i.name}</p>
                    {i.note && <p className="text-xs text-muted-foreground">{i.note}</p>}
                  </div>
                  <span className="text-sm">{formatCurrency(i.price * i.qty, restaurant.currency)}</span>
                </div>
              ))}
            </div>
            <div className="mt-4 flex justify-between font-semibold"><span>Total</span><span>{formatCurrency(cartTotal, restaurant.currency)}</span></div>
            <Button className="mt-4 w-full" size="lg" disabled={sending || cartList.length === 0} onClick={sendOrder}>
              {sending ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Enviar pedido'}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

function Header({ restaurant, tableNumber, onBack, onCallWaiter }) {
  return (
    <header className="sticky top-0 z-10 border-b border-border bg-background/90 backdrop-blur">
      <div className="mx-auto flex max-w-3xl items-center justify-between gap-3 p-4">
        <button onClick={onBack} className="flex items-center gap-2 min-w-0">
          <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl" style={{ background: `${restaurant.accent_color || '#e07a3c'}22` }}>
            <Flame className="h-5 w-5" style={{ color: restaurant.accent_color || '#e07a3c' }} />
          </div>
          <div className="min-w-0 text-left">
            <p className="truncate font-heading text-base font-semibold leading-tight">{restaurant.name}</p>
            <p className="text-xs text-muted-foreground">
              <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-2 py-0.5 font-medium text-primary">
                Mesa {tableNumber}
              </span>
            </p>
          </div>
        </button>
        {onCallWaiter && (
          <Button size="sm" variant="secondary" onClick={() => onCallWaiter('help')}>
            <Bell className="h-4 w-4" /> Chamar
          </Button>
        )}
      </div>
    </header>
  );
}