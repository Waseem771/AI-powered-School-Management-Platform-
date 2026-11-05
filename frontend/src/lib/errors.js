export const SERVER_UNREACHABLE_MESSAGE =
  'Could not reach the server. Check your internet connection and try again.';

function validationItemMessage(item) {
  if (typeof item?.msg !== 'string') return null;
  if (item.type === 'value_error') return item.msg;
  // Built-in messages do not say which field they mean.
  const field = String(item.loc?.[item.loc.length - 1] ?? '').replaceAll('_', ' ');
  return field && field !== 'body' ? `${field}: ${item.msg}` : item.msg;
}

/**
 * A message safe to show a user. The API's `detail` is a string for expected errors,
 * and a list of objects for validation errors, which must never be rendered directly.
 */
export function apiErrorMessage(error, fallback) {
  if (!error?.response) return SERVER_UNREACHABLE_MESSAGE;
  const detail = error.response.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    const messages = detail.map(validationItemMessage).filter(Boolean);
    if (messages.length > 0) return messages.join(' ');
  }
  return fallback;
}
