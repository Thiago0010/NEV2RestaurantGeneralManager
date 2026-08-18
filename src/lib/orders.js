// Uses api from restaurant-context
import { api } from '@/lib/restaurant-context';

export function recalcTotals(items, taxPercent = 0) {
  const subtotal = items.reduce((s, i) => s + Number(i.unit_price || 0) * Number(i.quantity || 0), 0);
  const service_tax = +(subtotal * (Number(taxPercent || 0) / 100)).toFixed(2);
  const total = +(subtotal + service_tax).toFixed(2);
  return { subtotal: +subtotal.toFixed(2), service_tax, total };
}

export async function refreshOrderTotals(orderId, taxPercent = 0) {
  const items = await api.OrderItem.filter({ order_id: orderId });
  const totals = recalcTotals(items, taxPercent);
  await api.Order.update(orderId, totals);
  return { items, ...totals };
}