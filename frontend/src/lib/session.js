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
