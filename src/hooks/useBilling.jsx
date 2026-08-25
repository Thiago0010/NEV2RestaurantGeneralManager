import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/restaurant-context";
import { useToast } from "@/components/ui/use-toast";
import { redirectToCheckout, redirectToPortal } from "@/lib/mercadopago";

// Static fallback — used if the backend isn't reachable (offline dev, etc.).
// Reflete o PLAN_CATALOG do backend (app/core/mercadopago.py):
//   Apenas 1 plano: "essencial" com display_name "Ilimitado".
const FALLBACK_PLANS = [
  { name: "essencial", display_name: "Ilimitado", base_price: 25438, commission_pct: 1.5, limits: { tables: 10000, employees: 1000, products: 721 } },
];

/**
 * Fetches the plan catalogue from the backend. Falls back to a hard-coded
 * list if the request fails (so the UI can still render during outages).
 */
export function useBillingPlans() {
  return useQuery({
    queryKey: ["billing", "plans"],
    queryFn: async () => {
      try {
        const res = await api.billing.getPlans();
        return res?.plans ?? FALLBACK_PLANS;
      } catch {
        return FALLBACK_PLANS;
      }
    },
    staleTime: 1000 * 60 * 60, // 1 hour
  });
}

/** Fetches the current restaurant's billing status. */
export function useBillingStatus() {
  return useQuery({
    queryKey: ["billing", "status"],
    queryFn: async () => {
      try {
        return await api.billing.getStatus();
      } catch {
        return null;
      }
    },
    staleTime: 1000 * 30,
  });
}

/** Creates a Mercado Pago checkout preference and redirects the user. */
export function useCreateCheckout() {
  const { toast } = useToast();
  return useMutation({
    mutationFn: async (plan) => {
      return await api.billing.createCheckout(plan);
    },
    onSuccess: async (response) => {
      try {
        await redirectToCheckout(response);
      } catch (err) {
        toast({
          title: "Erro ao redirecionar",
          description: err?.message ?? "Não foi possível abrir o checkout.",
          variant: "destructive",
        });
      }
    },
    onError: (err) => {
      toast({
        title: "Erro ao criar checkout",
        description: err?.message ?? "Tente novamente em instantes.",
        variant: "destructive",
      });
    },
  });
}

/** Opens the Mercado Pago portal in a new tab. */
export function useOpenPortal() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      return await api.billing.createPortal();
    },
    onSuccess: async (response) => {
      await redirectToPortal(response?.url ?? "/settings");
      // After returning from the portal the user might have changed
      // their plan — invalidate the cached status so the next page load
      // sees the fresh data.
      queryClient.invalidateQueries({ queryKey: ["billing", "status"] });
    },
    onError: (err) => {
      toast({
        title: "Erro ao abrir portal",
        description: err?.message ?? "Tente novamente.",
        variant: "destructive",
      });
    },
  });
}

export function formatPrice(cents) {
  return `R$ ${(cents / 100).toFixed(2).replace(".", ",")}`;
}
