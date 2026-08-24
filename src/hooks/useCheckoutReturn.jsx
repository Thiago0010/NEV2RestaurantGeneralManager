import { useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { useToast } from '@/components/ui/use-toast';
import { useBillingStatus } from '@/hooks/useBilling';
import { useRestaurant } from '@/lib/restaurant-context';

/**
 * Detecta o retorno do checkout do Mercado Pago em qualquer rota da app
 * (`?checkout=success|failure|pending`) e força a revalidação do status
 * de billing até que o webhook do MP atualize o restaurante para
 * ``active``/``trialing``. Quando isso acontece, libera tudo
 * automaticamente — o usuário não precisa dar reload.
 *
 * Idempotente: se o `?checkout=success` chegar repetido (ex: F5),
 * só processa uma vez por sessão de retorno.
 */
export function useCheckoutReturn() {
  const [searchParams, setSearchParams] = useSearchParams();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const { refetch: refetchBilling } = useBillingStatus();
  const { reload: reloadRestaurant } = useRestaurant();
  const processedRef = useRef(false);

  useEffect(() => {
    const status = searchParams.get('checkout');
    if (!status) return;

    // Evita processar o mesmo retorno duas vezes (F5, navegação back/forward).
    const dedupeKey = `nev2:checkout-return:${status}:${location.pathname}`;
    if (sessionStorage.getItem(dedupeKey)) {
      // Limpa o param e sai — já tratamos esse retorno.
      const next = new URLSearchParams(searchParams);
      next.delete('checkout');
      setSearchParams(next, { replace: true });
      return;
    }
    sessionStorage.setItem(dedupeKey, '1');

    // Invalida caches e força refetch imediato do status.
    queryClient.invalidateQueries({ queryKey: ['billing', 'status'] });

    const cleanup = () => {
      const next = new URLSearchParams(searchParams);
      next.delete('checkout');
      setSearchParams(next, { replace: true });
    };

    if (status === 'success') {
      toast({
        title: 'Pagamento aprovado',
        description: 'Confirmando sua assinatura…',
      });

      // Polling: o webhook do MP pode demorar alguns segundos pra chegar.
      // Batemos no /billing/status a cada 1.5s até virar active ou até
      // estourar o timeout (20s). Sem reload manual.
      let cancelled = false;
      const start = Date.now();
      const poll = async () => {
        for (let i = 0; i < 15 && !cancelled; i++) {
          await new Promise((r) => setTimeout(r, 1500));
          if (cancelled) return;
          try {
            queryClient.invalidateQueries({ queryKey: ['billing', 'status'] });
            const fresh = await refetchBilling();
            const s = fresh?.data?.plan_status;
            if (s === 'active' || s === 'trialing') {
              // Sincroniza o contexto do restaurante também — qualquer
              // página que leia `restaurant.plan_status` (ex: 402 handler)
              // já vê o estado novo.
              await reloadRestaurant();
              toast({
                title: 'Assinatura ativa',
                description: 'Tudo liberado! Aproveite o [NEV]2 Restaurant Management System.',
              });
              cleanup();
              return;
            }
          } catch {
            // tenta de novo — webhook pode estar chegando
          }
          if (Date.now() - start > 22_000) break;
        }
        if (!cancelled) {
          await reloadRestaurant();
          toast({
            title: 'Quase lá',
            description:
              'O pagamento foi aprovado. Se a assinatura não aparecer em alguns instantes, atualize a página.',
          });
          cleanup();
        }
      };
      poll();
      return () => {
        cancelled = true;
        processedRef.current = true;
      };
    }

    if (status === 'failure') {
      toast({
        title: 'Pagamento recusado',
        description: 'Tente novamente ou escolha outro método de pagamento.',
        variant: 'destructive',
      });
      cleanup();
      return;
    }

    if (status === 'pending') {
      toast({
        title: 'Pagamento pendente',
        description: 'Avisaremos assim que o pagamento for confirmado.',
        variant: 'warning',
      });
      cleanup();
      return;
    }

    // status desconhecido — só limpa o param
    cleanup();
  }, [searchParams, setSearchParams, queryClient, refetchBilling, reloadRestaurant, toast]);
}
