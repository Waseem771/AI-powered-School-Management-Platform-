/**
 * Which of the four things a data view should show. Failed always beats empty, so a server
 * problem can never look like "no records".
 *
 * @param {{ loading?: boolean, error?: string, count?: number }} view
 * @returns {'loading'|'error'|'empty'|'ready'}
 */
export function viewState({ loading, error, count }) {
  if (loading) return 'loading';
  if (error) return 'error';
  return count ? 'ready' : 'empty';
}

/** The next highlighted item in a list, wrapping at both ends. -1 means none, and there may be none. */
export function nextActiveIndex(current, change, count) {
  if (count === 0) return -1;
  if (current < 0) return change > 0 ? 0 : count - 1;
  return (current + change + count) % count;
}

/** Tab inside a dialog: returns the element to move to, or null to let the browser carry on. */
export function focusTrapTarget(focusable, active, shiftKey) {
  if (focusable.length === 0) return null;
  const first = focusable[0];
  const last = focusable[focusable.length - 1];
  if (shiftKey && active === first) return last;
  if (!shiftKey && active === last) return first;
  return null;
}

/** @param {{ name: string, roll_number: string, grade: string, section: string }} student */
export function studentLabel(student) {
  return `${student.name} (#${student.roll_number}, ${student.grade}-${student.section})`;
}

export const LIST_STEP = 25;

/** How many rows to show next when a long list is asked for more. Never more than exist. */
export function nextVisibleCount(current, total, step = LIST_STEP) {
  return Math.min(current + step, total);
}

/** "1 student", "2 students". */
export function countLabel(count, singular, plural = `${singular}s`) {
  return `${count} ${count === 1 ? singular : plural}`;
}

let nextToastId = 1;

/** A new list of toasts with one added, keeping only the latest few on screen. */
export function addToast(toasts, tone, message, limit = 3) {
  const toast = { id: nextToastId, tone, message };
  nextToastId += 1;
  return [...toasts, toast].slice(-limit);
}
