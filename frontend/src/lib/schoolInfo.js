/** Text for the page header, which says nothing rather than guess while the server has not answered. */
export function sessionLabel(info) {
  return info?.academic_session ? `Academic session ${info.academic_session}` : '';
}

/** "admin" becomes "Admin". */
export function roleLabel(role) {
  if (!role) return '';
  return role.charAt(0).toUpperCase() + role.slice(1);
}
