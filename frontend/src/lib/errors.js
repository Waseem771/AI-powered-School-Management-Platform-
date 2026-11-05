export const SERVER_UNREACHABLE_MESSAGE =
  'Could not reach the server. Check your internet connection and try again.';

/**
 * A message safe to show a user. The API's `detail` is a string for expected errors,
 * but a list of objects for validation errors, which must not be rendered directly.
 */
export function apiErrorMessage(error, fallback) {
  if (!error?.response) return SERVER_UNREACHABLE_MESSAGE;
  const detail = error.response.data?.detail;
  return typeof detail === 'string' ? detail : fallback;
}
