// Pure helpers for the "forgot password" screens, kept here so `npm test` can cover them.

export const MIN_PASSWORD_LENGTH = 10;

/**
 * The reset token from a link like /reset-password#token=abc. It travels after the "#", so it is never sent to a
 * server or put in a Referer header. Returns '' when there is none.
 */
export function readResetToken(hash) {
  const text = String(hash || '').replace(/^#/, '');
  const value = new URLSearchParams(text).get('token');
  return value ? value.trim() : '';
}

/** Plain-language reason a typed new password cannot be sent yet, or '' when it can. The server checks again. */
export function newPasswordProblem(password, confirmation) {
  if (!password || password.length < MIN_PASSWORD_LENGTH) {
    return `Your new password must be at least ${MIN_PASSWORD_LENGTH} characters.`;
  }
  if (password !== confirmation) return 'The two passwords do not match.';
  return '';
}

// The same rule as the server's (backend/services/email_address.py): exactly one plain mailbox, nothing a mail
// header could misread (no spaces, commas, quotes, brackets or line breaks, no display name, ASCII only).
const ATEXT = "[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+";
const LOCAL = new RegExp(`^${ATEXT}(?:\\.${ATEXT})*$`);
const LABEL = /^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$/;
const TLD = /^[A-Za-z]{2,63}$/;
// eslint-disable-next-line no-control-regex
const CONTROL = /[\u0000-\u001f\u007f]/;

/** True only for exactly one valid email address. A convenience for the form: the server decides. */
export function looksLikeEmail(value) {
  const text = String(value ?? '');
  if (CONTROL.test(text)) return false;
  const address = text.trim();
  if (!address || address.length > 254) return false;
  const parts = address.split('@');
  if (parts.length !== 2) return false;
  const [local, domain] = parts;
  if (local.length > 64 || !LOCAL.test(local)) return false;
  const labels = domain.split('.');
  return labels.length >= 2 && labels.every((label) => LABEL.test(label)) && TLD.test(labels[labels.length - 1]);
}

export const EMAIL_HELP = 'Enter one valid email address, such as name@example.com';
