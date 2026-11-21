const defaultUser = { username: 'admin', role: 'admin' };
const SESSION_KEY_PREFIX = 'educore_';

export function getStoredUser(storage = window.localStorage) {
  try {
    const storedUser = storage.getItem('educore_user');
    if (!storedUser) return defaultUser;

    const user = JSON.parse(storedUser);
    return user && typeof user === 'object' ? { ...defaultUser, ...user } : defaultUser;
  } catch {
    return defaultUser;
  }
}

/** Removes everything this app stored, including chat history, for the next person on this computer. */
export function clearSession(storage = window.localStorage) {
  const keys = [];
  for (let index = 0; index < storage.length; index += 1) {
    const key = storage.key(index);
    if (key?.startsWith(SESSION_KEY_PREFIX)) keys.push(key);
  }
  keys.forEach((key) => storage.removeItem(key));
}

/** What the server says while an administrator's reset is waiting for the owner to choose their own password. */
export const PASSWORD_CHANGE_REQUIRED = 'You must choose a new password before you can continue.';
export const CHANGE_PASSWORD_PATH = '/change-password';

/** True while the signed-in account must choose a new password before using anything else. Display only: the server refuses everything until then. */
export function mustChangePassword(user) {
  return user?.must_change_password === true;
}

/** Remembers that a change is required (or done), keeping the rest of the stored user. */
export function setPasswordChangeRequired(required, storage = window.localStorage) {
  const user = { ...getStoredUser(storage) };
  if (required) user.must_change_password = true;
  else delete user.must_change_password;
  storage.setItem('educore_user', JSON.stringify(user));
}
