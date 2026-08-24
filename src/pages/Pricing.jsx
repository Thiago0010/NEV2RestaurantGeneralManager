import React, { useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useToast } from '@/components/ui/use-toast';
import {
  useCreateCheckout,
  useBillingPlans,
  useBillingStatus,
  formatPrice,
} from '@/hooks/useBilling';
import { Button } from '@/components/ui/button';
import { AlertCircle, CheckCircle, Loader2 } from 'lucide-react';
import { useQueryClient } from '@tanstack/react-query';

export default function Pricing() {
  const { toast } = useToast();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const createCheckout = useCreateCheckout();
  const { data: plans = [], isLoading: loadingPlans } = useBillingPlans();
  const { refetch: refetchBillingStatus } = useBillingStatus();

  const handleSubscribe = (plan) => {
    createCheckout.mutate(plan);
  };

  // Handle checkout success/failure/pending from Mercado Pago redirect.
  // The webhook is async, so we poll for a few seconds after the redirect
  // and, on success, point the user straight to /settings so the active
  // subscription is visible immediately.
  useEffect(() => {
    const checkoutStatus = searchParams.get('checkout');
    if (!checkoutStatus) return;

    const next = new URLSearchParams(searchParams);
    next.delete('checkout');
    setSearchParams(next, { replace: true });

    if (checkoutStatus === 'success') {
      toast({ title: 'Pagamento aprovado', description: 'Confirmando sua assinatura…' });
      queryClient.invalidateQueries({ queryKey: ['billing', 'status'] });
      const poll = async () => {
        for (let i = 0; i < 10; i++) {
          await new Promise((r) => setTimeout(r, 1500));
          try {
            const fresh = await refetchBillingStatus();
            if (fresh?.data?.plan_status === 'active') {
              toast({ title: 'Assinatura ativa', description: 'Sua assinatura está ativa agora.' });
              navigate('/settings', { replace: true });
              return;
            }
          } catch { /* try again */ }
        }
        // Even if we didn't see ACTIVE in the window, send the user to
        // /settings so the UI can re-check there. The webhook may have
        // arrived just after our last poll.
        navigate('/settings', { replace: true });
      };
      poll();
    } else if (checkoutStatus === 'failure' || checkoutStatus === 'pending') {
      toast({
        title: checkoutStatus === 'failure' ? 'Pagamento recusado' : 'Pagamento pendente',
        description:
          checkoutStatus === 'failure'
            ? 'Seu pagamento foi recusado. Tente novamente ou escolha outro método.'
            : 'Seu pagamento está pendente de confirmação. Avisaremos assim que for aprovado.',
        variant: checkoutStatus === 'failure' ? 'destructive' : 'warning',
      });
    }
  }, [searchParams, setSearchParams, toast, queryClient, refetchBillingStatus, navigate]);

  return (
    <div className="space-y-6">
      <div className="text-center py-8">
        <AlertCircle className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
        <h1 className="font-heading text-4xl font-semibold">Escolha o plano ideal para o seu restaurante</h1>
        <p className="text-lg text-muted-foreground mt-2">
          Todos os planos incluem suporte, atualizações gratuitas e acesso a todas as funcionalidades.
        </p>
      </div>

      {loadingPlans ? (
        <div className="grid place-items-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <div className="grid gap-6 sm:grid-cols-1 lg:grid-cols-3">
          {plans.map((plan) => (
            <div key={plan.name} className="border rounded-xl p-6 flex flex-col h-full">
              <div className="mb-4">
                <h2 className="font-semibold text-xl">{plan.display_name}</h2>
                <p className="text-2xl font-bold">
                  {formatPrice(plan.base_price)}
                  <span className="text-base font-normal text-muted-foreground">/mês</span>
                </p>
              </div>

              <ul className="space-y-4 mb-6 flex-1">
                <li className="flex items-center gap-3 text-sm">
                  <CheckCircle className="h-4 w-4 text-green-500" />
                  <span>Comissão de {plan.commission_pct}% por pedido</span>
                </li>
                <li className="flex items-center gap-3 text-sm">
                  <CheckCircle className="h-4 w-4 text-green-500" />
                  <span>
                    Até {plan.limits.tables === 999 ? 'ilimitadas' : plan.limits.tables} mesas
                  </span>
                </li>
                <li className="flex items-center gap-3 text-sm">
                  <CheckCircle className="h-4 w-4 text-green-500" />
                  <span>
                    Até {plan.limits.employees === 999 ? 'ilimitados' : plan.limits.employees} funcionários
                  </span>
                </li>
                <li className="flex items-center gap-3 text-sm">
                  <CheckCircle className="h-4 w-4 text-green-500" />
                  <span>
                    Até {plan.limits.products === 9999 ? 'ilimitados' : plan.limits.products} produtos
                  </span>
                </li>
              </ul>

              <Button
                className="w-full"
                onClick={() => handleSubscribe(plan.name)}
                disabled={createCheckout.isPending}
              >
                {createCheckout.isPending ? 'Redirecionando...' : `Assinar ${plan.display_name}`}
              </Button>
            </div>
          ))}
        </div>
      )}

      <div className="border rounded-xl p-6 text-center">
        <h3 className="font-semibold mb-2">Perguntas frequentes</h3>
        <div className="space-y-3 text-sm text-muted-foreground">
          <p>
            <strong>Posso mudar de plano depois?</strong> Sim, você pode fazer upgrade ou
            downgrade a qualquer momento em <a href="/settings" className="underline">Configurações</a>.
          </p>
          <p>
            <strong>O que acontece se eu cancelar?</strong> Seu acesso continua até o fim do
            período pago, depois a conta volta para o plano gratuito.
          </p>
          <p>
            <strong>Como funciona a comissão?</strong> Cobramos uma pequena porcentagem apenas
            sobre os pedidos recebidos pelo sistema, sem taxas ocultas.
          </p>
        </div>
      </div>
    </div>
  );
}
