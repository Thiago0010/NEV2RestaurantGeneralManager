import React, { useState } from 'react';
import { api, useRestaurant } from '@/lib/restaurant-context';
import { slugify } from '@/lib/format';
import {
  Loader2,
  Save,
  CreditCard,
  AlertCircle,
  CheckCircle,
  Sparkles,
  Settings as SettingsIcon,
  XCircle,
  RotateCcw,
  ArrowUpRight,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
} from '@/components/ui/tabs';
import { useToast } from '@/components/ui/use-toast';
import {
  useCreateCheckout,
  useOpenPortal,
  useBillingPlans,
  useBillingStatus,
  formatPrice,
} from '@/hooks/useBilling';
import { useCheckoutReturn } from '@/hooks/useCheckoutReturn';

const ACCENTS = ['#e07a3c', '#c9a227', '#b85c3a', '#7a8c5a', '#9b6b4e', '#3a7a8c'];

const PLAN_STATUS_LABELS = {
  active: 'Ativo',
  trialing: 'Em teste',
  past_due: 'Pagamento atrasado',
  canceled: 'Cancelado',
  incomplete: 'Incompleto',
  incomplete_expired: 'Expirado',
  unpaid: 'Não pago',
  none: 'Sem plano',
};

const PLAN_STATUS_COLORS = {
  active: 'bg-green-100 text-green-800',
  trialing: 'bg-blue-100 text-blue-800',
  past_due: 'bg-yellow-100 text-yellow-800',
  canceled: 'bg-red-100 text-red-800',
  incomplete: 'bg-gray-100 text-gray-800',
  incomplete_expired: 'bg-gray-100 text-gray-800',
  unpaid: 'bg-red-100 text-red-800',
  none: 'bg-gray-100 text-gray-800',
};

export default function Settings() {
  const { restaurant, reload } = useRestaurant();
  const { toast } = useToast();
  const [tab, setTab] = useState('general');
  const [form, setForm] = useState({
    name: restaurant?.name || '',
    description: restaurant?.description || '',
    phone: restaurant?.phone || '',
    address: restaurant?.address || '',
    currency: restaurant?.currency || 'R$',
    service_tax_percent: restaurant?.service_tax_percent ?? 10,
    welcome_message: restaurant?.welcome_message || '',
    accent_color: restaurant?.accent_color || ACCENTS[0],
    logo_url: restaurant?.logo_url || '',
    cover_image: restaurant?.cover_image || '',
    slug: restaurant?.slug || '',
  });
  const [saving, setSaving] = useState(false);

  // Detecta retorno do checkout do MP e libera tudo automaticamente.
  useCheckoutReturn();

  const createCheckout = useCreateCheckout();
  const openPortal = useOpenPortal();
  const { data: plans = [] } = useBillingPlans();
  const { data: status } = useBillingStatus();

  const currentPlan = status?.plan_name || restaurant?.plan_name || 'none';
  const planStatus = status?.plan_status || restaurant?.plan_status || 'none';
  const currentPeriodEnd = status?.current_period_end || restaurant?.current_period_end;
  const cancelAtPeriodEnd = status?.cancel_at_period_end ?? restaurant?.cancel_at_period_end ?? false;
  const isTrial = status?.is_trial ?? planStatus === 'trialing';
  const trialEnd = status?.trial_end || restaurant?.trial_end;
  const daysUntilRenewal = status?.days_until_renewal;
  const hasSubscription = currentPlan && currentPlan !== 'none' && planStatus !== 'none';

  const save = async () => {
    setSaving(true);
    try {
      await api.restaurant.updateMine({
        name: form.name,
        description: form.description,
        phone: form.phone,
        address: form.address,
        currency: form.currency,
        service_tax_percent: Number(form.service_tax_percent),
        welcome_message: form.welcome_message,
        accent_color: form.accent_color,
        logo_url: form.logo_url,
        cover_image: form.cover_image,
        slug: slugify(form.slug || form.name),
      });
      await reload();
      toast({ title: 'Configurações salvas' });
    } catch (e) {
      toast({ title: 'Erro ao salvar', description: e?.message, variant: 'destructive' });
    } finally {
      setSaving(false);
    }
  };

  const handleSubscribe = (plan) => {
    createCheckout.mutate(plan);
  };

  const handleOpenPortal = () => {
    openPortal.mutate();
  };

  const handleChangePlan = (planName) => {
    // Mudar de plano = abrir checkout para o novo plano. O MP cuida da
    // proratação. Se o plano atual é o mesmo, não faz nada.
    if (planName === currentPlan && !cancelAtPeriodEnd) {
      toast({
        title: 'Você já está neste plano',
        description: 'Escolha um plano diferente para mudar.',
      });
      return;
    }
    createCheckout.mutate(planName);
  };

  const handleCancelAtPeriodEnd = () => {
    if (!confirm(
      'Cancelar a assinatura?\n\n' +
      'Sua assinatura continuará ativa até o fim do período atual. ' +
      'Você pode reativá-la a qualquer momento antes do vencimento.'
    )) return;
    // Como o MP gerencia o cancelamento, abrimos o portal onde o usuário
    // pode confirmar. (A página do portal mostra o botão "Cancelar".)
    openPortal.mutate();
  };

  if (!restaurant) {
    return (
      <div className="grid h-full place-items-center">
        <Loader2 className="h-7 w-7 animate-spin text-primary" />
      </div>
    );
  }

  const currentPlanInfo = plans.find((p) => p.name === currentPlan);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-heading text-3xl font-semibold">Configurações</h1>
        <p className="text-sm text-muted-foreground">
          Identidade, regras e faturamento do seu estabelecimento.
        </p>
      </div>

      <Tabs value={tab} onValueChange={setTab} className="w-full max-w-3xl">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="general" className="gap-2">
            <SettingsIcon className="h-4 w-4" />
            Geral
          </TabsTrigger>
          <TabsTrigger value="subscription" className="gap-2">
            <CreditCard className="h-4 w-4" />
            Assinatura
          </TabsTrigger>
        </TabsList>

        {/* ============================================================ */}
        {/* ABA: Configurações Gerais                                     */}
        {/* ============================================================ */}
        <TabsContent value="general" className="mt-6">
          <Card className="max-w-2xl">
            <CardHeader>
              <CardTitle>Identidade do estabelecimento</CardTitle>
            </CardHeader>
            <CardContent className="space-y-5 p-6 pt-0">
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <Label>Nome</Label>
                  <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
                </div>
                <div className="space-y-1.5">
                  <Label>Slug (URL pública)</Label>
                  <Input value={form.slug} onChange={(e) => setForm({ ...form, slug: e.target.value })} />
                  <p className="text-xs text-muted-foreground">/r/{slugify(form.slug || form.name)}</p>
                </div>
              </div>
              <div className="space-y-1.5">
                <Label>Descrição</Label>
                <Textarea rows={2} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <Label>Telefone</Label>
                  <Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
                </div>
                <div className="space-y-1.5">
                  <Label>Endereço</Label>
                  <Input value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} />
                </div>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <Label>Moeda</Label>
                  <Input value={form.currency} onChange={(e) => setForm({ ...form, currency: e.target.value })} />
                </div>
                <div className="space-y-1.5">
                  <Label>Taxa de serviço (%)</Label>
                  <Input
                    type="number"
                    min={0}
                    value={form.service_tax_percent}
                    onChange={(e) => setForm({ ...form, service_tax_percent: e.target.value })}
                  />
                </div>
              </div>
              <div className="space-y-1.5">
                <Label>Mensagem de boas-vindas (QR)</Label>
                <Textarea
                  rows={2}
                  value={form.welcome_message}
                  onChange={(e) => setForm({ ...form, welcome_message: e.target.value })}
                />
              </div>
              <div className="space-y-1.5">
                <Label>Cor de destaque</Label>
                <div className="flex gap-2 pt-1">
                  {ACCENTS.map((c) => (
                    <button
                      key={c}
                      type="button"
                      onClick={() => setForm({ ...form, accent_color: c })}
                      className={`h-8 w-8 rounded-full border-2 ${form.accent_color === c ? 'border-foreground' : 'border-transparent'}`}
                      style={{ background: c }}
                    />
                  ))}
                </div>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <Label>Logo (URL)</Label>
                  <Input value={form.logo_url} onChange={(e) => setForm({ ...form, logo_url: e.target.value })} />
                </div>
                <div className="space-y-1.5">
                  <Label>Capa (URL)</Label>
                  <Input value={form.cover_image} onChange={(e) => setForm({ ...form, cover_image: e.target.value })} />
                </div>
              </div>
              <Button onClick={save} disabled={saving}>
                <Save className="h-4 w-4" /> {saving ? 'Salvando...' : 'Salvar'}
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ============================================================ */}
        {/* ABA: Assinatura / Faturamento                                 */}
        {/* ============================================================ */}
        <TabsContent value="subscription" className="mt-6 space-y-6">
          {/* Banner de trial */}
          {isTrial && (
            <Card className="max-w-2xl border-blue-200 bg-blue-50/60">
              <CardContent className="p-5">
                <div className="flex items-start gap-3">
                  <Sparkles className="h-5 w-5 mt-0.5 text-blue-600 flex-shrink-0" />
                  <div className="flex-1">
                    <p className="font-medium text-blue-900">Você está no trial gratuito</p>
                    <p className="text-sm text-blue-800/80 mt-1">
                      {trialEnd
                        ? `Expira em ${new Date(trialEnd).toLocaleDateString('pt-BR')}${
                            daysUntilRenewal != null ? ` (${daysUntilRenewal} dia${daysUntilRenewal === 1 ? '' : 's'})` : ''
                          }.`
                        : 'Aproveite para testar todas as funcionalidades.'}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Plano atual */}
          {hasSubscription ? (
            <Card className="max-w-2xl">
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  <span>Plano atual</span>
                  <span
                    className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      PLAN_STATUS_COLORS[planStatus] || 'bg-gray-100 text-gray-800'
                    }`}
                  >
                    {PLAN_STATUS_LABELS[planStatus] || planStatus}
                  </span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4 p-6 pt-0">
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-1">
                    <p className="text-xs text-muted-foreground">Plano</p>
                    <p className="font-medium text-lg">
                      {currentPlanInfo?.display_name || currentPlan}
                    </p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-xs text-muted-foreground">Comissão por pedido</p>
                    <p className="font-medium">{currentPlanInfo?.commission_pct ?? 0}%</p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-xs text-muted-foreground">
                      {isTrial ? 'Trial expira em' : 'Próxima renovação'}
                    </p>
                    <p className="font-medium">
                      {currentPeriodEnd ? new Date(currentPeriodEnd).toLocaleDateString('pt-BR') : '—'}
                      {cancelAtPeriodEnd && (
                        <span className="text-xs text-destructive ml-1">(cancelamento agendado)</span>
                      )}
                    </p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-xs text-muted-foreground">Valor mensal</p>
                    <p className="font-medium">
                      {currentPlanInfo ? formatPrice(currentPlanInfo.base_price) : '—'}
                    </p>
                  </div>
                </div>

                <div className="rounded-lg border border-border bg-muted/30 p-4 text-sm space-y-1">
                  <p className="font-medium">Benefícios inclusos:</p>
                  <ul className="space-y-1 text-muted-foreground">
                    <li>• Até {currentPlanInfo?.limits?.tables === 999 ? 'ilimitadas' : currentPlanInfo?.limits?.tables} mesas</li>
                    <li>• Até {currentPlanInfo?.limits?.employees === 999 ? 'ilimitados' : currentPlanInfo?.limits?.employees} funcionários</li>
                    <li>• Até {currentPlanInfo?.limits?.products === 9999 ? 'ilimitados' : currentPlanInfo?.limits?.products} produtos</li>
                  </ul>
                </div>

                <div className="flex flex-wrap gap-2 pt-2 border-t">
                  <Button onClick={handleOpenPortal} disabled={openPortal.isPending} variant="default">
                    <CreditCard className="h-4 w-4" />
                    {openPortal.isPending ? 'Abrindo...' : 'Gerenciar pagamento'}
                  </Button>
                  {cancelAtPeriodEnd ? (
                    <Button
                      variant="outline"
                      onClick={handleOpenPortal}
                      disabled={openPortal.isPending}
                    >
                      <RotateCcw className="h-4 w-4" />
                      Reativar assinatura
                    </Button>
                  ) : (
                    <Button
                      variant="outline"
                      onClick={handleCancelAtPeriodEnd}
                      disabled={openPortal.isPending}
                    >
                      <XCircle className="h-4 w-4" />
                      Cancelar ao fim do período
                    </Button>
                  )}
                </div>
                <p className="text-xs text-muted-foreground">
                  Mudanças de plano, método de pagamento, cancelamento e faturas são
                  gerenciados pelo portal do Mercado Pago.
                </p>
              </CardContent>
            </Card>
          ) : (
            <Card className="max-w-2xl">
              <CardContent className="p-6 text-center">
                <AlertCircle className="h-10 w-10 text-muted-foreground mx-auto mb-2" />
                <h3 className="font-semibold">Nenhum plano ativo</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  Escolha um plano abaixo para começar a usar o sistema completo.
                </p>
              </CardContent>
            </Card>
          )}

          {/* Mudança de plano */}
          {plans.length > 0 && (
            <Card className="max-w-2xl">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <ArrowUpRight className="h-5 w-5" />
                  {hasSubscription ? 'Mudar de plano' : 'Planos disponíveis'}
                </CardTitle>
              </CardHeader>
              <CardContent className="p-6 pt-0">
                <div className="grid gap-4 sm:grid-cols-3">
                  {plans.map((plan) => {
                    const isCurrent = plan.name === currentPlan && hasSubscription;
                    return (
                      <div
                        key={plan.name}
                        className={`relative border rounded-xl p-4 flex flex-col ${
                          isCurrent ? 'border-primary bg-primary/5' : ''
                        }`}
                      >
                        {isCurrent && (
                          <span className="absolute -top-2 right-3 rounded-full bg-primary px-2 py-0.5 text-[10px] font-semibold uppercase text-primary-foreground">
                            Atual
                          </span>
                        )}
                        <div className="mb-3">
                          <h4 className="font-semibold">{plan.display_name}</h4>
                          <p className="text-2xl font-bold">
                            {formatPrice(plan.base_price)}
                            <span className="text-base font-normal text-muted-foreground">/mês</span>
                          </p>
                        </div>

                        <ul className="space-y-2 mb-4 flex-1">
                          <li className="flex items-center gap-2 text-sm">
                            <CheckCircle className="h-4 w-4 text-green-500 flex-shrink-0" />
                            <span>Comissão de {plan.commission_pct}% por pedido</span>
                          </li>
                          <li className="flex items-center gap-2 text-sm">
                            <CheckCircle className="h-4 w-4 text-green-500 flex-shrink-0" />
                            <span>Até {plan.limits.tables === 999 ? 'ilimitadas' : plan.limits.tables} mesas</span>
                          </li>
                          <li className="flex items-center gap-2 text-sm">
                            <CheckCircle className="h-4 w-4 text-green-500 flex-shrink-0" />
                            <span>Até {plan.limits.employees === 999 ? 'ilimitados' : plan.limits.employees} funcionários</span>
                          </li>
                          <li className="flex items-center gap-2 text-sm">
                            <CheckCircle className="h-4 w-4 text-green-500 flex-shrink-0" />
                            <span>Até {plan.limits.products === 9999 ? 'ilimitados' : plan.limits.products} produtos</span>
                          </li>
                        </ul>

                        <Button
                          className="w-full mt-auto"
                          variant={isCurrent ? 'outline' : 'default'}
                          onClick={() => handleChangePlan(plan.name)}
                          disabled={createCheckout.isPending || (isCurrent && !cancelAtPeriodEnd)}
                        >
                          {createCheckout.isPending
                            ? 'Redirecionando...'
                            : isCurrent
                              ? 'Plano atual'
                              : hasSubscription
                                ? `Mudar para ${plan.display_name}`
                                : `Assinar ${plan.display_name}`}
                        </Button>
                      </div>
                    );
                  })}
                </div>
                <p className="text-xs text-muted-foreground mt-4">
                  {hasSubscription
                    ? 'A mudança de plano gera um novo pagamento proporcional ao período restante.'
                    : 'Você pode cancelar a qualquer momento. Pagamentos processados pelo Mercado Pago.'}
                </p>
              </CardContent>
            </Card>
          )}

          {/* Dicas / ajuda */}
          <Card className="max-w-2xl">
            <CardHeader>
              <CardTitle>Como funciona</CardTitle>
            </CardHeader>
            <CardContent className="p-6 pt-0 text-sm text-muted-foreground space-y-2">
              <p>
                <strong className="text-foreground">Cobrança:</strong> uma assinatura mensal
                fixa por estabelecimento mais uma pequena comissão por pedido fechado.
              </p>
              <p>
                <strong className="text-foreground">Cancele quando quiser:</strong> o cancelamento
                é feito pelo portal do Mercado Pago e tem efeito imediato. Você não será cobrado
                no próximo ciclo.
              </p>
              <p>
                <strong className="text-foreground">Reativação:</strong> se você cancelar, é só
                reassinar pelo mesmo botão. Os dados do restaurante ficam preservados.
              </p>
              <p>
                <strong className="text-foreground">Faturas e pagamentos:</strong> acesse o portal
                para ver o histórico completo, atualizar cartão e baixar recibos.
              </p>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
