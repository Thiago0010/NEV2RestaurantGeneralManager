import React from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertTriangle, MessageCircle, Mail, LogOut, Sparkles, CreditCard } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useRestaurant } from '@/lib/restaurant-context';

// Canais oficiais de suporte — exibidos quando o restaurante não tem plano
// ativo. O usuário pode escolher entre WhatsApp ou e-mail.
const SUPPORT_WHATSAPP_NUMBER = '5561998889542'; // +55 (61) 9 9888-9542
const SUPPORT_WHATSAPP_DISPLAY = '+55 (61) 9 9888-9542';
const SUPPORT_EMAIL = 'thiagohenriquetech@gmail.com';

function buildWhatsAppUrl(planName, planStatus) {
  const text = encodeURIComponent(
    `Olá! Preciso de ajuda com a assinatura do [NEV]2 Restaurant Management System.\n` +
      `Plano atual: ${planName || 'nenhum'}\n` +
      `Status: ${planStatus || 'desconhecido'}\n` +
      `Quero regularizar o acesso ao sistema.`,
  );
  return `https://wa.me/${SUPPORT_WHATSAPP_NUMBER}?text=${text}`;
}

function buildMailtoUrl(planName, planStatus) {
  const subject = encodeURIComponent('[NEV]2 Restaurant Management System — Regularização de assinatura');
  const body = encodeURIComponent(
    `Olá,\n\n` +
      `Preciso de ajuda para regularizar minha assinatura do [NEV]2 Restaurant Management System.\n\n` +
      `Plano atual: ${planName || 'nenhum'}\n` +
      `Status: ${planStatus || 'desconhecido'}\n\n` +
      `Aguardo o retorno. Obrigado!`,
  );
  return `mailto:${SUPPORT_EMAIL}?subject=${subject}&body=${body}`;
}

/**
 * Overlay de tela cheia que bloqueia o uso do app quando o restaurante
 * não tem um plano ativo. Mantém visíveis as rotas em que o usuário
 * precisa resolver o problema (settings/pricing) e expõe os canais
 * oficiais de suporte (WhatsApp e e-mail).
 */
export default function PlanBlockedOverlay({ planName, planStatus }) {
  const navigate = useNavigate();
  const { api } = useRestaurant();

  const handleGoToSettings = () => {
    navigate('/settings', { replace: true });
  };

  const handleGoToPricing = () => {
    navigate('/pricing', { replace: true });
  };

  const handleLogout = async () => {
    if (api?.auth?.logout) {
      await api.auth.logout();
    } else {
      localStorage.removeItem('access_token');
      window.location.replace('/login');
    }
  };

  const whatsappUrl = buildWhatsAppUrl(planName, planStatus);
  const mailtoUrl = buildMailtoUrl(planName, planStatus);

  // Mensagem principal de acordo com o status recebido do backend.
  const isTrialExpired = planStatus === 'canceled' || planStatus === 'incomplete_expired';
  const headline = isTrialExpired
    ? 'Seu período de teste terminou'
    : 'Você ainda não tem um plano ativo';

  const subheadline = isTrialExpired
    ? 'Para continuar usando o [NEV]2 Restaurant Management System, escolha um plano agora. Seu trial acabou e o acesso está pausado até a ativação.'
    : 'Para começar a usar o sistema, é só escolher um plano. A ativação é imediata após o pagamento.';

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="plan-blocked-title"
      className="fixed inset-0 z-[100] flex items-center justify-center overflow-y-auto bg-gradient-to-br from-background via-background to-muted/60 p-4"
      data-testid="plan-blocked-overlay"
    >
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(224,122,60,0.12),_transparent_60%)]" />

      <div className="relative w-full max-w-xl rounded-2xl border border-border bg-card shadow-2xl">
        <div className="absolute -top-3 left-1/2 -translate-x-1/2">
          <div className="flex h-12 w-12 items-center justify-center rounded-full border-4 border-card bg-destructive text-destructive-foreground shadow-lg">
            <AlertTriangle className="h-5 w-5" />
          </div>
        </div>

        <div className="px-6 pt-10 pb-6 sm:px-8 sm:pt-12 sm:pb-8">
          <div className="text-center">
            <p className="text-xs font-semibold uppercase tracking-widest text-destructive">
              Acesso bloqueado
            </p>
            <h1
              id="plan-blocked-title"
              className="mt-2 font-heading text-2xl font-semibold text-foreground sm:text-3xl"
            >
              {headline}
            </h1>
            <p className="mt-3 text-sm text-muted-foreground sm:text-base">
              {subheadline}
            </p>
          </div>

          {isTrialExpired && (
            <div className="mt-6 flex items-start gap-3 rounded-xl border border-blue-200 bg-blue-50/70 p-4 text-sm text-blue-900">
              <Sparkles className="h-5 w-5 mt-0.5 flex-shrink-0" />
              <div>
                <p className="font-medium">Seu trial expirou</p>
                <p className="mt-1 text-xs sm:text-sm">
                  Escolha um plano abaixo para reativar o acesso. Seus dados
                  continuam seguros e tudo volta a funcionar na hora.
                </p>
              </div>
            </div>
          )}

          <div className="mt-6 grid gap-3 sm:grid-cols-2">
            <Button
              onClick={handleGoToSettings}
              size="lg"
              className="w-full"
              data-testid="plan-blocked-choose"
            >
              <CreditCard className="h-4 w-4" />
              Escolher um plano
            </Button>
            <Button
              onClick={handleGoToPricing}
              size="lg"
              variant="outline"
              className="w-full"
              data-testid="plan-blocked-pricing"
            >
              Ver planos e preços
            </Button>
          </div>

          <div className="mt-8 border-t border-border pt-6">
            <p className="text-center text-xs font-semibold uppercase tracking-widest text-muted-foreground">
              Precisa de ajuda? Fale com o suporte
            </p>
            <p className="mt-2 text-center text-sm text-muted-foreground">
              Se tiver qualquer dúvida sobre o plano, pagamento ou renovação, é só chamar nos canais abaixo.
            </p>

            <div className="mt-5 grid gap-3 sm:grid-cols-2">
              <a
                href={whatsappUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="group flex items-center gap-3 rounded-xl border border-border bg-background/60 p-4 transition-colors hover:border-green-500/50 hover:bg-green-50"
                data-testid="plan-blocked-whatsapp"
              >
                <span className="grid h-10 w-10 place-items-center rounded-full bg-green-100 text-green-700 group-hover:bg-green-500 group-hover:text-white transition-colors">
                  <MessageCircle className="h-5 w-5" />
                </span>
                <span className="min-w-0">
                  <span className="block text-xs font-medium uppercase tracking-wide text-muted-foreground">
                    WhatsApp
                  </span>
                  <span className="block truncate text-sm font-semibold text-foreground">
                    {SUPPORT_WHATSAPP_DISPLAY}
                  </span>
                </span>
              </a>

              <a
                href={mailtoUrl}
                className="group flex items-center gap-3 rounded-xl border border-border bg-background/60 p-4 transition-colors hover:border-primary/50 hover:bg-primary/5"
                data-testid="plan-blocked-email"
              >
                <span className="grid h-10 w-10 place-items-center rounded-full bg-primary/10 text-primary group-hover:bg-primary group-hover:text-primary-foreground transition-colors">
                  <Mail className="h-5 w-5" />
                </span>
                <span className="min-w-0">
                  <span className="block text-xs font-medium uppercase tracking-wide text-muted-foreground">
                    E-mail
                  </span>
                  <span className="block truncate text-sm font-semibold text-foreground">
                    {SUPPORT_EMAIL}
                  </span>
                </span>
              </a>
            </div>

            <p className="mt-4 text-center text-xs text-muted-foreground">
              Atendimento de segunda a sexta, das 8h às 18h.
            </p>
          </div>

          <div className="mt-6 flex items-center justify-center">
            <button
              type="button"
              onClick={handleLogout}
              className="inline-flex items-center gap-2 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground"
            >
              <LogOut className="h-3.5 w-3.5" />
              Sair da conta
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
