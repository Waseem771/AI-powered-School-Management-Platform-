export const MODEL_NOTE = 'Trained on synthetic data. Not validated on real students. A teacher should review before acting.';

export const NOT_ENOUGH_DATA = 'Not enough data';

export const RISK_BANDS = [
  { key: 'all', label: 'All students', detail: 'Current students' },
  { key: 'High', label: 'High', detail: 'Score above 70' },
  { key: 'Medium', label: 'Medium', detail: 'Score 40 to 70' },
  { key: 'Low', label: 'Low', detail: 'Score below 40' },
  { key: NOT_ENOUGH_DATA, label: NOT_ENOUGH_DATA, detail: 'Too few marks to estimate' },
];

const BAND_STYLES = {
  High: { badge: 'bg-rose-100 text-rose-800 border-rose-200', card: 'border-rose-300/80', dot: 'bg-rose-500' },
  Medium: { badge: 'bg-amber-100 text-amber-800 border-amber-200', card: 'border-amber-300/80', dot: 'bg-amber-500' },
  Low: { badge: 'bg-emerald-100 text-emerald-800 border-emerald-200', card: 'border-slate-200/80', dot: 'bg-emerald-500' },
};
const NO_ESTIMATE_STYLE = { badge: 'bg-slate-100 text-slate-700 border-slate-200', card: 'border-slate-200/80', dot: 'bg-slate-400' };

/** @param {string} category @returns {{ badge: string, card: string, dot: string }} */
export function bandStyle(category) {
  return BAND_STYLES[category] ?? NO_ESTIMATE_STYLE;
}

/** @param {string} category @returns {string} */
export function bandLabel(category) {
  return category === NOT_ENOUGH_DATA ? category : `${category} estimate`;
}

/** A score out of 100, never a percentage: it is not a measured probability of anything. */
export function scoreText(score) {
  return score === null || score === undefined ? 'No score' : `Score ${score} of 100`;
}

/** @param {Array<{ risk_category: string }>} students @param {string} band */
export function studentsInBand(students, band) {
  return band === 'all' ? students : students.filter((student) => student.risk_category === band);
}

/** @param {Array<{ risk_category: string }>} students */
export function bandCounts(students) {
  return Object.fromEntries(RISK_BANDS.map(({ key }) => [key, studentsInBand(students, key).length]));
}

/** @param {{ needed?: boolean, overdue_invoices?: number, overdue_amount?: number } | undefined} followUp */
export function feeFollowUpText(followUp) {
  if (!followUp?.needed) return null;
  const count = followUp.overdue_invoices;
  return `Fee follow-up: ${count} overdue invoice${count === 1 ? '' : 's'}, Rs ${Number(followUp.overdue_amount).toLocaleString()}`;
}

/** @param {{ grade_trend: number|null }} metrics */
export function trendText(metrics) {
  const change = metrics?.grade_trend;
  if (change === null || change === undefined) return 'No midterm and final to compare';
  if (change === 0) return 'No change, midterm to final';
  return `${change > 0 ? 'Up' : 'Down'} ${Math.abs(change)} points, midterm to final`;
}

/** @param {string|null} method */
export function explanationTitle(method) {
  return method === 'shap' ? 'What moved this estimate most' : 'From the student\'s record';
}
