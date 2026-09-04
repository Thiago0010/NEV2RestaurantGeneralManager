/**
 * Mercado Pago redirect helpers.
 *
 * Mercado Pago's Checkout Pro is a hosted page, so all we need to do is a
 * `window.location.href` to the `init_point` returned by the backend. In
 * sandbox/dev mode we prefer `sandbox_init_point` so the user can pay with
 * the test cards without going through real money.
 *
 * For the "portal" flow there is no Stripe-equivalent hosted page. We just
 * return the URL the backend gave us, which points at MP's subscription
 * management page (or our own /settings page for empty portal URLs).
 */

const isSandbox = () => {
  // Treat any non-prod deploy (or no token at all) as sandbox. This is
  // intentionally loose so devs don't get a 502 from MP for trying to
  // pay with a test card in production.
  if (typeof import.meta.env.VITE_MP_PUBLIC_KEY === "string") {
    const publicKey = import.meta.env.VITE_MP_PUBLIC_KEY;
    return publicKey.startsWith("pk_test_") || publicKey.startsWith("TEST-");
  }
  return true;
};

/**
 * Redirect the user to the Mercado Pago checkout. Prefers the sandbox URL
 * when the public key indicates a test environment.
 */
export const redirectToCheckout = async (response) => {
  let url;
  if (typeof response === "string") {
    url = response;
  } else {
    url = isSandbox() && response?.sandbox_url ? response.sandbox_url : response?.url;
  }
  if (!url) {
    throw new Error("Mercado Pago não retornou uma URL de checkout válida.");
  }
  window.location.href = url;
};

/**
 * Redirect the user to the Mercado Pago portal / subscription management
 * page. If the backend returns a relative path (e.g. `/settings`), we just
 * navigate there directly.
 */
export const redirectToPortal = async (portalUrl) => {
  if (!portalUrl) {
    window.location.href = "/settings";
    return;
  }
  // If it's a relative path, navigate the SPA; otherwise it's a full URL.
  if (portalUrl.startsWith("/")) {
    window.location.href = portalUrl;
  } else {
    window.location.href = portalUrl;
  }
};

/**
 * Show a non-fatal toast if Mercado Pago redirects with a known error.
 * Currently unused but exported so the Settings page can pick it up later.
 */
export const notifyCheckoutResult = (toast, result) => {
  if (!result) return;
  if (result === "success") {
    toast({
      title: "Pagamento aprovado",
      description: "Sua assinatura está ativa agora.",
    });
  } else if (result === "failure") {
    toast({
      title: "Pagamento recusado",
      description: "Tente novamente ou escolha outro método de pagamento.",
      variant: "destructive",
    });
  } else {
    toast({
      title: "Pagamento pendente",
      description: "Avisaremos assim que o pagamento for confirmado.",
    });
  }
};
