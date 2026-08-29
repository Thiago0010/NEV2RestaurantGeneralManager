import React, { useEffect, useState } from 'react';
import { api } from '@/lib/restaurant-context';
import { useRestaurant, userRestaurantId } from '@/lib/restaurant-context';
import { Plus, Pencil, Trash2, Loader2, Copy, Check, KeyRound, UserPlus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogClose, DialogDescription
} from '@/components/ui/dialog';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from '@/components/ui/select';
import { useToast } from '@/components/ui/use-toast';

const ROLE_LABEL = { manager: 'Gerente', waiter: 'Garçom', kitchen: 'Cozinha' };

const emptyForm = {
  name: '',
  email: '',
  password: '',
  role: 'waiter',
  phone: '',
  is_active: true,
};

export default function Employees() {
  const { user } = useRestaurant();
  const rid = userRestaurantId(user);
  const { toast } = useToast();
  const [list, setList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [edit, setEdit] = useState(null);
  const [form, setForm] = useState(emptyForm);
  const [saving, setSaving] = useState(false);
  // Quando criamos um funcionário com email/senha, devolvemos as credenciais
  // pro dono copiar e entregar ao funcionário. Mantemos aqui por sessão.
  const [createdCredentials, setCreatedCredentials] = useState(null);
  const [copied, setCopied] = useState(false);

  const load = async () => {
    setList(await api.Employee.filter({ restaurant_id: rid }, 'name', 500));
    setLoading(false);
  };
  useEffect(() => { if (rid) load();   }, [rid]);

  const openCreate = () => {
    setEdit(null);
    setForm(emptyForm);
    setCreatedCredentials(null);
    setOpen(true);
  };

  const openEdit = (e) => {
    setEdit(e);
    setForm({
      name: e.name || '',
      email: e.email || '',
      password: '', // nunca exibimos a senha atual
      role: e.role || 'waiter',
      phone: e.phone || '',
      is_active: e.is_active ?? true,
    });
    setCreatedCredentials(null);
    setOpen(true);
  };

  const save = async () => {
    if (!form.name.trim()) {
      toast({ title: 'Informe o nome', variant: 'destructive' });
      return;
    }
    // Validação simples de email quando preenchido (modo criar exige email).
    if (!edit && !form.email.trim()) {
      toast({ title: 'Informe o e-mail de login', variant: 'destructive' });
      return;
    }
    if (!edit && form.password && form.password.length < 6) {
      toast({ title: 'A senha precisa ter pelo menos 6 caracteres', variant: 'destructive' });
      return;
    }
    if (!edit && form.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim())) {
      toast({ title: 'E-mail inválido', variant: 'destructive' });
      return;
    }

    setSaving(true);
    try {
      if (edit) {
        // Edição: atualiza Employee (nome, role, telefone, ativo). Email/senha
        // são gerenciados pela conta de usuário — para trocá-los, peça ao
        // funcionário para usar "esqueci a senha".
        await api.Employee.update(edit.id, {
          name: form.name.trim(),
          role: form.role,
          phone: form.phone,
          is_active: form.is_active,
        });
        toast({ title: 'Funcionário atualizado' });
        setOpen(false);
      } else {
        // Criação: gera um User com email/senha e cria o Employee vinculado.
        const result = await api.auth.createStaff(
          form.email.trim(),
          form.password,
          form.name.trim(),
          form.role
        );
        // Vincula o user_id ao employee existente (ou cria o employee).
        if (result?.id) {
          try {
            await api.Employee.create({
              restaurant_id: rid,
              user_id: result.id,
              name: form.name.trim(),
              role: form.role,
              phone: form.phone,
              is_active: form.is_active,
            });
          } catch (e) {
            // Se o backend já criar via POST /employees com user, esse erro é ok.
            console.warn('Employee link warn:', e);
          }
        }
        // Mostra as credenciais para o dono copiar e entregar ao funcionário.
        setCreatedCredentials({
          email: form.email.trim(),
          password: form.password,
          name: form.name.trim(),
        });
        toast({ title: 'Funcionário criado!', description: 'Copie as credenciais e entregue ao funcionário.' });
      }
      await load();
    } catch (e) {
      toast({ title: edit ? 'Erro ao atualizar' : 'Erro ao criar funcionário', description: e?.message, variant: 'destructive' });
    } finally {
      setSaving(false);
    }
  };

  const remove = async (e) => {
    if (!confirm(`Remover ${e.name}?`)) return;
    try {
      await api.Employee.delete(e.id);
      await load();
      toast({ title: 'Funcionário removido' });
    } catch (err) {
      toast({ title: 'Erro ao remover', description: err?.message, variant: 'destructive' });
    }
  };

  const toggle = async (e) => {
    try {
      await api.Employee.update(e.id, { is_active: !e.is_active });
      await load();
    } catch (err) {
      toast({ title: 'Erro', description: err?.message, variant: 'destructive' });
    }
  };

  const copyCreds = async () => {
    if (!createdCredentials) return;
    const txt = `Olá ${createdCredentials.name}!\n\nSuas credenciais de acesso ao painel do garçom:\n\nE-mail: ${createdCredentials.email}\nSenha: ${createdCredentials.password}\n\nAcesse em: ${window.location.origin}/login`;
    try {
      await navigator.clipboard.writeText(txt);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
      toast({ title: 'Credenciais copiadas!' });
    } catch {
      toast({ title: 'Não foi possível copiar', variant: 'destructive' });
    }
  };

  if (loading) return <div className="grid h-full place-items-center"><Loader2 className="h-7 w-7 animate-spin text-primary" /></div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-heading text-3xl font-semibold">Funcionários</h1>
          <p className="text-sm text-muted-foreground">
            Equipe do estabelecimento. Ao adicionar, você cria a conta de acesso.
          </p>
        </div>
        <Button onClick={openCreate}><UserPlus className="h-4 w-4" /> Novo funcionário</Button>
      </div>

      {list.length === 0 ? (
        <div className="surface-card grid h-48 place-items-center text-center text-sm text-muted-foreground">
          <div>
            <p className="font-medium text-foreground">Nenhum funcionário cadastrado</p>
            <p>Adicione sua equipe para registrar atendimentos e acessar o painel.</p>
          </div>
        </div>
      ) : (
        <div className="surface-card overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-secondary/50 text-left text-xs uppercase tracking-wider text-muted-foreground">
              <tr>
                <th className="p-4">Nome</th>
                <th className="p-4">Função</th>
                <th className="p-4">E-mail</th>
                <th className="p-4">Telefone</th>
                <th className="p-4">Status</th>
                <th className="p-4 text-right">Ações</th>
              </tr>
            </thead>
            <tbody>
              {list.map((e) => (
                <tr key={e.id} className="border-t border-border">
                  <td className="p-4 font-medium">{e.name}</td>
                  <td className="p-4">{ROLE_LABEL[e.role] || e.role}</td>
                  <td className="p-4 text-muted-foreground">{e.email || '—'}</td>
                  <td className="p-4 text-muted-foreground">{e.phone || '—'}</td>
                  <td className="p-4">
                    <label className="flex items-center gap-2">
                      <Switch checked={e.is_active} onCheckedChange={() => toggle(e)} />
                      <span className="text-xs">{e.is_active ? 'Ativo' : 'Inativo'}</span>
                    </label>
                  </td>
                  <td className="p-4">
                    <div className="flex justify-end gap-1">
                      <button onClick={() => openEdit(e)} className="rounded-lg p-1.5 text-muted-foreground hover:text-foreground" title="Editar">
                        <Pencil className="h-4 w-4" />
                      </button>
                      <button onClick={() => remove(e)} className="rounded-lg p-1.5 text-muted-foreground hover:text-destructive" title="Remover">
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{edit ? 'Editar funcionário' : 'Novo funcionário'}</DialogTitle>
            <DialogDescription>
              {edit
                ? 'Atualize os dados do funcionário. Email e senha são gerenciados pelo próprio usuário.'
                : 'Crie a conta de acesso. Após salvar, copie as credenciais e entregue ao funcionário.'}
            </DialogDescription>
          </DialogHeader>

          {!edit && !createdCredentials && (
            <div className="space-y-4 py-2">
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="space-y-1.5 sm:col-span-2">
                  <Label>Nome completo</Label>
                  <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="João Pedro da Silva" />
                </div>
                <div className="space-y-1.5 sm:col-span-2">
                  <Label>E-mail (login)</Label>
                  <Input
                    type="email"
                    value={form.email}
                    onChange={(e) => setForm({ ...form, email: e.target.value })}
                    placeholder="joao@email.com"
                    autoComplete="off"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label className="flex items-center gap-1"><KeyRound className="h-3 w-3" /> Senha</Label>
                  <Input
                    type="text"
                    value={form.password}
                    onChange={(e) => setForm({ ...form, password: e.target.value })}
                    placeholder="Mínimo 6 caracteres"
                    autoComplete="new-password"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label>Telefone</Label>
                  <Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} placeholder="(11) 99999-9999" />
                </div>
                <div className="space-y-1.5 sm:col-span-2">
                  <Label>Função</Label>
                  <Select value={form.role} onValueChange={(v) => setForm({ ...form, role: v })}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="waiter">Garçom</SelectItem>
                      <SelectItem value="manager">Gerente</SelectItem>
                      <SelectItem value="kitchen">Cozinha</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <label className="flex items-center gap-2 text-sm sm:col-span-2">
                  <Switch checked={form.is_active} onCheckedChange={(v) => setForm({ ...form, is_active: v })} />
                  Ativo
                </label>
              </div>
            </div>
          )}

          {!edit && createdCredentials && (
            <div className="space-y-4 py-2">
              <div className="rounded-lg border border-green-200 bg-green-50 p-4 space-y-2">
                <p className="text-sm font-medium text-green-900">
                  ✓ Funcionário criado com sucesso!
                </p>
                <p className="text-xs text-green-800">
                  Copie as credenciais abaixo e envie para o funcionário. Esta tela não mostrará a senha novamente.
                </p>
              </div>
              <div className="rounded-lg border bg-muted/30 p-4 space-y-2 text-sm">
                <div>
                  <span className="text-xs text-muted-foreground">Nome</span>
                  <p className="font-medium">{createdCredentials.name}</p>
                </div>
                <div>
                  <span className="text-xs text-muted-foreground">E-mail (login)</span>
                  <p className="font-mono">{createdCredentials.email}</p>
                </div>
                <div>
                  <span className="text-xs text-muted-foreground">Senha</span>
                  <p className="font-mono">{createdCredentials.password}</p>
                </div>
                <div>
                  <span className="text-xs text-muted-foreground">Link de acesso</span>
                  <p className="font-mono text-xs break-all">{window.location.origin}/login</p>
                </div>
              </div>
              <Button onClick={copyCreds} variant="outline" className="w-full">
                {copied ? <Check className="h-4 w-4 text-green-600" /> : <Copy className="h-4 w-4" />}
                {copied ? 'Copiado!' : 'Copiar credenciais'}
              </Button>
            </div>
          )}

          {edit && (
            <div className="space-y-4 py-2">
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="space-y-1.5 sm:col-span-2">
                  <Label>Nome completo</Label>
                  <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
                </div>
                <div className="space-y-1.5 sm:col-span-2">
                  <Label>E-mail</Label>
                  <Input value={form.email} disabled placeholder="(gerenciado pelo próprio usuário)" />
                  <p className="text-xs text-muted-foreground">Para trocar a senha, peça ao funcionário para usar "Esqueci a senha" no login.</p>
                </div>
                <div className="space-y-1.5">
                  <Label>Telefone</Label>
                  <Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
                </div>
                <div className="space-y-1.5">
                  <Label>Função</Label>
                  <Select value={form.role} onValueChange={(v) => setForm({ ...form, role: v })}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="waiter">Garçom</SelectItem>
                      <SelectItem value="manager">Gerente</SelectItem>
                      <SelectItem value="kitchen">Cozinha</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <label className="flex items-center gap-2 text-sm sm:col-span-2">
                  <Switch checked={form.is_active} onCheckedChange={(v) => setForm({ ...form, is_active: v })} />
                  Ativo
                </label>
              </div>
            </div>
          )}

          <DialogFooter>
            {!edit && createdCredentials ? (
              <DialogClose asChild>
                <Button>Concluir</Button>
              </DialogClose>
            ) : (
              <>
                <DialogClose asChild><Button variant="outline">Cancelar</Button></DialogClose>
                <Button onClick={save} disabled={saving}>
                  {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                  {edit ? 'Salvar' : 'Criar e gerar credenciais'}
                </Button>
              </>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
