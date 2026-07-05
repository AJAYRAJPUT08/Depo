import { formatCurrency } from "../lib/format";

export default function MetricCards({ summary }) {
  const cards = [
    {
      color: "blue",
      label: "Total Employees",
      value: summary?.total_employees ?? 0,
      sub: "Today",
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
          <circle cx="9" cy="7" r="4" />
          <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
          <path d="M16 3.13a4 4 0 0 1 0 7.75" />
        </svg>
      ),
    },
    {
      color: "green",
      label: "Currently Inside",
      value: summary?.currently_inside ?? 0,
      sub: "Employees",
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
          <circle cx="9" cy="7" r="4" />
          <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
          <path d="M16 3.13a4 4 0 0 1 0 7.75" />
        </svg>
      ),
    },
    {
      color: "purple",
      label: "Total Working Hours",
      value: `${summary?.total_hours_today ?? 0} hrs`,
      sub: "Today",
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="10" />
          <polyline points="12 6 12 12 16 14" />
        </svg>
      ),
    },
    {
      color: "orange",
      label: "Total Payment Generated",
      value: formatCurrency(summary?.total_payment_today),
      sub: "Today",
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="10" />
          <path d="M12 6v12M9 9.5c0-1.4 1.3-2.5 3-2.5s3 1.1 3 2.5-1.3 2.5-3 2.5-3 1.1-3 2.5 1.3 2.5 3 2.5 3-1.1 3-2.5" />
        </svg>
      ),
    },
  ];

  return (
    <div className="metric-cards">
      {cards.map((c) => (
        <div className="metric-card" key={c.label}>
          <div className={`metric-icon ${c.color}`}>{c.icon}</div>
          <div className="metric-info">
            <span className="metric-label">{c.label}</span>
            <div className="metric-value">{c.value}</div>
            <span className="metric-sub">{c.sub}</span>
          </div>
        </div>
      ))}
    </div>
  );
}
