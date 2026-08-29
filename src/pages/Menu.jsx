import React, { useEffect, useState } from 'react';
import { api } from '@/lib/restaurant-context';
import { useRestaurant, userRestaurantId } from '@/lib/restaurant-context';
import { formatCurrency } from '@/lib/format';
import { Plus, Pencil, Trash2, Loader2, Star, Utensils } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogClose
} from '@/components/ui/dialog';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from '@/components/ui/select';
import { useToast } from '@/components/ui/use-toast';

export default function Menu() {
  return (
    <Tabs defaultValue="products" className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-heading text-3xl font-semibold">Cardápio</h1>
          <p className="text-sm text-muted-foreground">Categorias e produtos do seu menu.</p>
        </div>
        <TabsList>
          <TabsTrigger value="products">Produtos</TabsTrigger>
          <TabsTrigger value="categories">Categorias</TabsTrigger>
        </TabsList>
      </div>
      <TabsContent value="products"><Products /></TabsContent>
      <TabsContent value="categories"><Categories /></TabsContent>
    </Tabs>
  );
}

function Categories() {
  const { user } = useRestaurant();
  const rid = userRestaurantId(user);
  const { toast } = useToast();
  const [list, setList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [name, setName] = useState('');

  const load = async () => {
      setList(await api.Category.filter({ restaurant_id: rid }, 'sort_order', 500));
      setLoading(false);
    };
  useEffect(() => { if (rid) load();   }, [rid]);

  const save = async () => {
      if (!name.trim()) return;
      await api.Category.create({ restaurant_id: rid, name: name.trim(), sort_order: list.length });
      setName(''); setOpen(false); load();
      toast({ title: 'Categoria criada' });
    };
    const remove = async (c) => { await api.Category.delete(c.id); load(); };

  if (loading) return <Spinner />;
  return (
    <div className="space-y-4">
      <Button onClick={() => setOpen(true)}><Plus className="h-4 w-4" /> Nova categoria</Button>
      {list.length === 0 ? <Empty text="Nenhuma categoria ainda." /> : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {list.map((c) => (
            <div key={c.id} className="surface-card flex items-center justify-between p-4">
              <span className="font-medium">{c.name}</span>
              <button onClick={() => remove(c)} className="text-muted-foreground hover:text-destructive"><Trash2 className="h-4 w-4" /></button>
            </div>
          ))}
        </div>
      )}
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>Nova categoria</DialogTitle></DialogHeader>
          <div className="space-y-1.5 py-2">
            <Label>Nome</Label>
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Entradas" />
          </div>
          <DialogFooter>
            <DialogClose asChild><Button variant="outline">Cancelar</Button></DialogClose>
            <Button onClick={save}>Criar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function Products() {
  const { user, restaurant } = useRestaurant();
  const rid = userRestaurantId(user);
  const { toast } = useToast();
  const [products, setProducts] = useState([]);
  const [cats, setCats] = useState([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [edit, setEdit] = useState(null);
  const [form, setForm] = useState({ name: '', description: '', price: '', category_id: '', image_url: '', is_available: true, featured: false });

  const load = async () => {
      const [p, c] = await Promise.all([
        api.Product.filter({ restaurant_id: rid }, '-created_date', 1000),
        api.Category.filter({ restaurant_id: rid }, 'sort_order', 500),
      ]);
      setProducts(p); setCats(c); setLoading(false);
    };
  useEffect(() => { if (rid) load();   }, [rid]);

  const catName = (id) => cats.find((c) => c.id === id)?.name || '—';

  const save = async () => {
      if (!form.name.trim() || !form.price) { toast({ title: 'Nome e preço são obrigatórios', variant: 'destructive' }); return; }
      const payload = {
        restaurant_id: rid,
        name: form.name.trim(),
        description: form.description,
        price: Number(form.price),
        category_id: form.category_id,
        image_url: form.image_url,
        is_available: form.is_available,
        featured: form.featured,
      };
      if (edit) await api.Product.update(edit.id, payload);
      else await api.Product.create(payload);
      setOpen(false); setEdit(null);
      setForm({ name: '', description: '', price: '', category_id: '', image_url: '', is_available: true, featured: false });
      load();
      toast({ title: edit ? 'Produto atualizado' : 'Produto criado' });
    };

    const toggle = async (p, field) => {
      await api.Product.update(p.id, { [field]: !p[field] });
      load();
    };
    const remove = async (p) => { await api.Product.delete(p.id); load(); };

  if (loading) return <Spinner />;
  return (
    <div className="space-y-4">
      <Button onClick={() => { setEdit(null); setForm({ name: '', description: '', price: '', category_id: '', image_url: '', is_available: true, featured: false }); setOpen(true); }}>
        <Plus className="h-4 w-4" /> Novo produto
      </Button>
      {products.length === 0 ? <Empty text="Nenhum produto ainda. Crie categorias primeiro." /> : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {products.map((p) => (
            <div key={p.id} className={`surface-card overflow-hidden ${!p.is_available ? 'opacity-60' : ''}`}>
              <div className="relative h-32 bg-secondary">
                {p.image_url ? (
                  <img src={p.image_url} alt={p.name} className="h-full w-full object-cover" />
                ) : (
                  <div className="grid h-full place-items-center text-muted-foreground"><Utensils className="h-8 w-8" /></div>
                )}
                {p.featured && <span className="absolute left-2 top-2 rounded-full bg-accent/90 px-2 py-0.5 text-xs font-medium text-accent-foreground"><Star className="mr-1 inline h-3 w-3" />Destaque</span>}
                {!p.is_available && <span className="absolute right-2 top-2 rounded-full bg-destructive px-2 py-0.5 text-xs font-medium text-destructive-foreground">Indisponível</span>}
              </div>
              <div className="p-4">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="truncate font-medium">{p.name}</p>
                    <p className="text-xs text-muted-foreground">{catName(p.category_id)}</p>
                  </div>
                  <span className="font-heading font-semibold text-primary">{formatCurrency(p.price, restaurant?.currency)}</span>
                </div>
                {p.description && <p className="mt-2 line-clamp-2 text-xs text-muted-foreground">{p.description}</p>}
                <div className="mt-3 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-muted-foreground">Disponível</span>
                    <Switch checked={p.is_available} onCheckedChange={() => toggle(p, 'is_available')} />
                  </div>
                  <div className="flex gap-1">
                    <button onClick={() => { setEdit(p); setForm({ name: p.name, description: p.description, price: String(p.price), category_id: p.category_id, image_url: p.image_url, is_available: p.is_available, featured: p.featured }); setOpen(true); }} className="rounded-lg p-1.5 text-muted-foreground hover:text-foreground"><Pencil className="h-4 w-4" /></button>
                    <button onClick={() => remove(p)} className="rounded-lg p-1.5 text-muted-foreground hover:text-destructive"><Trash2 className="h-4 w-4" /></button>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader><DialogTitle>{edit ? 'Editar produto' : 'Novo produto'}</DialogTitle></DialogHeader>
          <div className="grid gap-4 py-2">
            <div className="grid gap-2 sm:grid-cols-2">
              <div className="space-y-1.5"><Label>Nome</Label><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></div>
              <div className="space-y-1.5"><Label>Preço</Label><Input type="number" step="0.01" value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })} /></div>
            </div>
            <div className="space-y-1.5"><Label>Descrição</Label><Textarea rows={2} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></div>
            <div className="grid gap-2 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label>Categoria</Label>
                <Select value={form.category_id} onValueChange={(v) => setForm({ ...form, category_id: v })}>
                  <SelectTrigger><SelectValue placeholder="Selecione" /></SelectTrigger>
                  <SelectContent>{cats.map((c) => <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5"><Label>Imagem (URL)</Label><Input value={form.image_url} onChange={(e) => setForm({ ...form, image_url: e.target.value })} placeholder="https://..." /></div>
            </div>
            <div className="flex items-center gap-6">
              <label className="flex items-center gap-2 text-sm"><Switch checked={form.is_available} onCheckedChange={(v) => setForm({ ...form, is_available: v })} /> Disponível</label>
              <label className="flex items-center gap-2 text-sm"><Switch checked={form.featured} onCheckedChange={(v) => setForm({ ...form, featured: v })} /> Destaque</label>
            </div>
          </div>
          <DialogFooter>
            <DialogClose asChild><Button variant="outline">Cancelar</Button></DialogClose>
            <Button onClick={save}>{edit ? 'Salvar' : 'Criar'}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function Spinner() { return <div className="grid h-full place-items-center"><Loader2 className="h-7 w-7 animate-spin text-primary" /></div>; }
function Empty({ text }) { return <div className="surface-card grid h-40 place-items-center text-sm text-muted-foreground">{text}</div>; }