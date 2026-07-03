export function formatCurrency(amount) {
  const n = Number(amount || 0);
  return "₹" + n.toLocaleString("en-IN", { maximumFractionDigits: 0 });
}

export function formatCurrencyPrecise(amount) {
  const n = Number(amount || 0);
  return "₹" + n.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function formatRate(rate) {
  return rate ? `₹${Number(rate).toLocaleString("en-IN")} / hr` : "—";
}

export function formatDateDisplay(dateStr) {
  if (!dateStr) return "—";
  const [y, m, d] = dateStr.split("-");
  return `${d}-${m}-${y}`;
}
