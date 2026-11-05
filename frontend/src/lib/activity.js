import { formatRupees } from './fees.js';

/** One line of the dashboard's recent activity, from a real record. */
export function activityText(item) {
  if (item.kind === 'payment') return `${formatRupees(item.amount)} received for ${item.month}`;
  if (item.kind === 'challan') return `${formatRupees(item.amount)} challan issued for ${item.month}`;
  return `Enrolled in ${item.class_name}`;
}

/** A date from the server, as a person reads it. */
export function formatDate(iso, options = { day: 'numeric', month: 'short', year: 'numeric' }) {
  if (!iso) return 'Not recorded';
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? 'Not recorded' : date.toLocaleDateString('en-GB', options);
}
