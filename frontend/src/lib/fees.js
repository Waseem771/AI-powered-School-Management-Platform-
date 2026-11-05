const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];
const DEFAULT_DUE_DAY = '10';

/** "2026-11", the value of a month picker, for a given date. */
export function monthPickerValue(today = new Date()) {
  const month = String(today.getMonth() + 1).padStart(2, '0');
  return `${today.getFullYear()}-${month}`;
}

/** "2026-11" becomes "November 2026", the format the API stores. */
export function monthLabel(pickerValue) {
  const [year, month] = pickerValue.split('-');
  return `${MONTH_NAMES[Number(month) - 1]} ${year}`;
}

/** Fees are due on the 10th under the school's fee policy. */
export function defaultDueDate(pickerValue) {
  return `${pickerValue}-${DEFAULT_DUE_DAY}`;
}

export function challanFormError({ amount, month, due_date: dueDate }) {
  if (!month) return 'Choose the billing month.';
  if (!dueDate) return 'Choose the due date.';
  if (!(Number(amount) > 0)) return 'Enter a fee amount greater than zero.';
  return null;
}

export function paymentAmountError(amountText, balance) {
  const amount = Number(amountText);
  if (!amountText || !(amount > 0)) return 'Enter an amount greater than zero.';
  if (amount > balance) return `The amount is more than the Rs. ${balance.toLocaleString()} still owed.`;
  return null;
}

export function formatRupees(amount) {
  return `Rs. ${(amount ?? 0).toLocaleString()}`;
}
