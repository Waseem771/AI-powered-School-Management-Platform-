const defaultUser = { username: 'admin', role: 'admin' };

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
