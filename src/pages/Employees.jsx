import React, { useEffect, useState } from 'react';
import { api } from '@/lib/restaurant-context';
import { useRestaurant, userRestaurantId } from '@/lib/restaurant-context';
import { Plus, Pencil, Trash2, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogClose
} from '@/components/ui/dialog';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from '@/components/ui/select';
import { useToast } from '@/components/ui/use-toast';

const ROLE_LABEL = { manager: 'Gerente', waiter: 'Garçom', kitchen: 'Cozinha' };

export default function Employees() {
  const { user } = useRestaurant();
  const rid = userRestaurantId(user);
  const { toast } = useToast();
  const [list, setList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [edit, setEdit] = useState(null);
  const [form, setForm] = useState({ name: '', role: 'waiter', phone: '', active: true });

  const load = async () => {
      setList(await api.Employee.filter({ restaurant_id: rid }, 'name', 500));
      setLoading(false);
    };
  useEffect(() => { if (rid) load(); /* eslint-disable-next-line */ }, [rid]);

  const save = async () => {
      if (!form.name.trim()) { toast({ title: 'Informe o nome', variant: 'destructive' }); return; }
      const payload = { restaurant_id: rid, name: form.name.trim(), role: form.role, phone: form.phone, active: form.active };
      if (edit) await api.Employee.update(edit.id, payload);
      else await api.Employee.create(payload);
      setOpen(false); setEdit(null); setForm({ name: '', role: 'waiter', phone: '', active: true });
      load(); toast({ title: edit ? 'Funcionário atualizado' : 'Funcionário adicionado' });
    };
    const remove = async (e) => { await api.Employee.delete(e.id); load(); };
    const toggle = async (e) => { await api.Employee.update(e.id, { active: !e.active }); load(); };

  if (loading) return <div className="grid h-full place-items-center"><Loader2 className="h-7 w-7 animate-spin text-primary" /></div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-heading text-3xl font-semibold">Funcionários</h1>
          <p className="text-sm text-muted-foreground">Equipe do estabelecimento.</p>
        </div>
        <Button onClick={() => { setEdit(null); setForm({ name: '', role: 'waiter', phone: '', active: true }); setOpen(true); }}><Plus className="h-4 w-4" /> Novo funcionário</Button>
      </div>

      {list.length === 0 ? (
        <div className="surface-card grid h-48 place-items-center text-center text-sm text-muted-foreground">
          <div><p className="font-medium text-foreground">Nenhum funcionário cadastrado</p><p>Adicione sua equipe para registrar atendimentos.</p></div>
        </div>
      ) : (
        <div className="surface-card overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-secondary/50 text-left text-xs uppercase tracking-wider text-muted-foreground">
              <tr><th className="p-4">Nome</th><th className="p-4">Função</th><th className="p-4">Telefone</th><th className="p-4">Status</th><th className="p-4 text-right">Ações</th></tr>
            </thead>
            <tbody>
              {list.map((e) => (
                <tr key={e.id} className="border-t border-border">
                  <td className="p-4 font-medium">{e.name}</td>
                  <td className="p-4">{ROLE_LABEL[e.role] || e.role}</td>
                  <td className="p-4 text-muted-foreground">{e.phone || '—'}</td>
                  <td className="p-4">
                    <label className="flex items-center gap-2"><Switch checked={e.active} onCheckedChange={() => toggle(e)} /><span className="text-xs">{e.active ? 'Ativo' : 'Inativo'}</span></label>
                  </td>
                  <td className="p-4">
                    <div className="flex justify-end gap-1">
                      <button onClick={() => { setEdit(e); setForm({ name: e.name, role: e.role, phone: e.phone, active: e.active }); setOpen(true); }} className="rounded-lg p-1.5 text-muted-foreground hover:text-foreground"><Pencil className="h-4 w-4" /></button>
                      <button onClick={() => remove(e)} className="rounded-lg p-1.5 text-muted-foreground hover:text-destructive"><Trash2 className="h-4 w-4" /></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>{edit ? 'Editar funcionário' : 'Novo funcionário'}</DialogTitle></DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-1.5"><Label>Nome completo</Label><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="João Pedro da Silva" /></div>
            <div className="grid gap-2 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label>Função</Label>
                <Select value={form.role} onValueChange={(v) => setForm({ ...form, role: v })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="manager">Gerente</SelectItem>
                    <SelectItem value="waiter">Garçom</SelectItem>
                    <SelectItem value="kitchen">Cozinha</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5"><Label>Telefone</Label><Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></div>
            </div>
            <label className="flex items-center gap-2 text-sm"><Switch checked={form.active} onCheckedChange={(v) => setForm({ ...form, active: v })} /> Ativo</label>
          </div>
          <DialogFooter>
            <DialogClose asChild><Button variant="outline">Cancelar</Button></DialogClose>
            <Button onClick={save}>{edit ? 'Salvar' : 'Adicionar'}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}