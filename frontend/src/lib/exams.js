const PROMOTION_STYLES = {
  promoted: 'bg-emerald-100 text-emerald-800 border-emerald-200',
  not_promoted: 'bg-rose-100 text-rose-800 border-rose-200',
  incomplete: 'bg-amber-100 text-amber-800 border-amber-200',
};
const NEUTRAL_STYLE = 'bg-slate-100 text-slate-700 border-slate-200';

export function promotionStyle(status) {
  return PROMOTION_STYLES[status] ?? NEUTRAL_STYLE;
}

/** A short badge. The full wording, such as which subjects are missing, is shown beside it. */
export function promotionBadge(promotion) {
  if (promotion?.status === 'promoted') return 'Promoted';
  if (promotion?.status === 'not_promoted') return 'Not promoted';
  if (promotion?.status === 'incomplete') return 'Not decided yet';
  return null;
}

/** One option in the exam picker, such as "Final Term (2025-2026)". */
export function examLabel(exam) {
  return exam.session ? `${exam.exam_type} (${exam.session})` : exam.exam_type;
}

export function examKey(exam) {
  return `${exam.academic_year_id ?? ''}|${exam.exam_type}`;
}

/** Query parameters that ask the API for exactly this exam. */
export function examParams(exam) {
  if (!exam) return {};
  const params = { exam_type: exam.exam_type };
  if (exam.academic_year_id != null) params.academic_year_id = exam.academic_year_id;
  return params;
}
