export function extractErrorMessage(error, fallback = 'Erro ao processar a solicitação.') {
  if (!error) return fallback;

  if (typeof error === 'string') return error || fallback;

  if (typeof error?.message === 'string' && error.message.trim()) {
    return error.message.trim();
  }

  if (typeof error?.detail === 'string' && error.detail.trim()) {
    return error.detail.trim();
  }

  if (typeof error?.error === 'string' && error.error.trim()) {
    return error.error.trim();
  }

  if (Array.isArray(error?.detail) && error.detail.length) {
    const first = error.detail[0];
    if (typeof first === 'string') return first;
    if (typeof first?.msg === 'string') return first.msg;
  }

  if (typeof error?.message === 'object' && error.message) {
    const nested = extractErrorMessage(error.message, fallback);
    if (nested && nested !== fallback) return nested;
  }

  if (typeof error?.detail === 'object' && error.detail) {
    const nested = extractErrorMessage(error.detail, fallback);
    if (nested && nested !== fallback) return nested;
  }

  return fallback;
}
