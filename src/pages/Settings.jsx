import React, { useState } from 'react';
import { api } from '@/lib/restaurant-context';
import { useRestaurant } from '@/lib/restaurant-context';
import { slugify } from '@/lib/format';
import { Loader2, Save } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { useToast } from '@/components/ui/use-toast';

const ACCENTS = ['#e07a3c', '#c9a227', '#b85c3a', '#7a8c5a', '#9b6b4e', '#3a7a8c'];

export default function Settings() {
  const { restaurant, setRestaurant, reload } = useRestaurant();
  const { toast } = useToast();
  const [form, setForm] = useState({
    name: restaurant?.name || '', description: restaurant?.description || '', phone: restaurant?.phone || '',
    address: restaurant?.address || '', currency: restaurant?.currency || 'R$', service_tax_percent: restaurant?.service_tax_percent ?? 10,
    welcome_message: restaurant?.welcome_message || '', accent_color: restaurant?.accent_color || '#e07a3c',
    logo_url: restaurant?.logo_url || '', cover_image: restaurant?.cover_image || '', slug: restaurant?.slug || '',
  });
  const [saving, setSaving] = useState(false);

  const save = async () => {
      setSaving(true);
      try {
        await api.restaurant.updateMine({
          name: form.name, description: form.description, phone: form.phone, address: form.address,
          currency: form.currency, service_tax_percent: Number(form.service_tax_percent), welcome_message: form.welcome_message,
          accent_color: form.accent_color, logo_url: form.logo_url, cover_image: form.cover_image, slug: slugify(form.slug || form.name),
        });
        await reload();
        toast({ title: 'Configurações salvas' });
      } catch (e) {
        toast({ title: 'Erro ao salvar', description: e?.message, variant: 'destructive' });
      } finally {
        setSaving(false);
      }
    };

  if (!restaurant) return <div className="grid h-full place-items-center"><Loader2 className="h-7 w-7 animate-spin text-primary" /></div>;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-heading text-3xl font-semibold">Configurações</h1>
        <p className="text-sm text-muted-foreground">Identidade e regras do seu estabelecimento.</p>
      </div>

      <div className="surface-card max-w-2xl space-y-5 p-6">
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-1.5"><Label>Nome</Label><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></div>
          <div className="space-y-1.5"><Label>Slug (URL pública)</Label><Input value={form.slug} onChange={(e) => setForm({ ...form, slug: e.target.value })} /><p className="text-xs text-muted-foreground">/r/{slugify(form.slug || form.name)}</p></div>
        </div>
        <div className="space-y-1.5"><Label>Descrição</Label><Textarea rows={2} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-1.5"><Label>Telefone</Label><Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></div>
          <div className="space-y-1.5"><Label>Endereço</Label><Input value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} /></div>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-1.5"><Label>Moeda</Label><Input value={form.currency} onChange={(e) => setForm({ ...form, currency: e.target.value })} /></div>
          <div className="space-y-1.5"><Label>Taxa de serviço (%)</Label><Input type="number" min={0} value={form.service_tax_percent} onChange={(e) => setForm({ ...form, service_tax_percent: e.target.value })} /></div>
        </div>
        <div className="space-y-1.5"><Label>Mensagem de boas-vindas (QR)</Label><Textarea rows={2} value={form.welcome_message} onChange={(e) => setForm({ ...form, welcome_message: e.target.value })} /></div>
        <div className="space-y-1.5"><Label>Cor de destaque</Label>
          <div className="flex gap-2 pt-1">
            {ACCENTS.map((c) => (
              <button key={c} type="button" onClick={() => setForm({ ...form, accent_color: c })}
                className={`h-8 w-8 rounded-full border-2 ${form.accent_color === c ? 'border-foreground' : 'border-transparent'}`} style={{ background: c }} />
            ))}
          </div>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-1.5"><Label>Logo (URL)</Label><Input value={form.logo_url} onChange={(e) => setForm({ ...form, logo_url: e.target.value })} /></div>
          <div className="space-y-1.5"><Label>Capa (URL)</Label><Input value={form.cover_image} onChange={(e) => setForm({ ...form, cover_image: e.target.value })} /></div>
        </div>
        <Button onClick={save} disabled={saving}><Save className="h-4 w-4" /> {saving ? 'Salvando...' : 'Salvar'}</Button>
      </div>
    </div>
  );
}