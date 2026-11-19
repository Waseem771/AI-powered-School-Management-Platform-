/**
 * Which screens each kind of account sees. This only decides what the app shows and where it sends
 * people. The backend refuses every request a role may not make, whatever this file says.
 */
export const STAFF_HOME = '/dashboard';
export const TEACHER_HOME = '/teacher/dashboard';
export const SESSION_ENDED_REASON = 'ended';

const STAFF_NAV = [
  { to: '/dashboard', label: 'Dashboard', icon: 'dashboard' },
  { to: '/students', label: 'Students', icon: 'students' },
  { to: '/fees', label: 'Fees', icon: 'fees' },
  { to: '/results', label: 'Exam Results', icon: 'results' },
  { to: '/at-risk', label: 'Academic Early Warning', icon: 'atRisk' },
  { to: '/chatbot', label: 'School Assistant', icon: 'chatbot' },
  { to: '/admissions', label: 'Admissions', icon: 'admissions' },
];
const TEACHERS_NAV = { to: '/teachers', label: 'Teachers', icon: 'teachers' };
const TEACHER_NAV = [
  { to: '/teacher/dashboard', label: 'Teacher Dashboard', icon: 'dashboard' },
  { to: '/teacher/profile', label: 'My Profile', icon: 'profile' },
];

const roleOf = (user) => String(user?.role ?? '').toLowerCase();

export function isTeacher(user) {
  return roleOf(user) === 'teacher';
}

export function isAdmin(user) {
  return roleOf(user) === 'admin';
}

export function homePathFor(user) {
  return isTeacher(user) ? TEACHER_HOME : STAFF_HOME;
}

export function navItemsFor(user) {
  if (isTeacher(user)) return TEACHER_NAV;
  return isAdmin(user) ? [...STAFF_NAV, TEACHERS_NAV] : STAFF_NAV;
}

/** True when this account has a screen at `pathname`. Whole path segments are compared, so "/teachers" is not "/teacher". */
export function canAccessPath(user, pathname) {
  const firstSegment = String(pathname ?? '').split('/').filter(Boolean)[0] ?? '';
  if (isTeacher(user)) return firstSegment === 'teacher';
  if (firstSegment === 'teacher') return false;
  if (firstSegment === 'teachers') return isAdmin(user);
  return true;
}

export function sessionEndedPath() {
  return `/login?reason=${SESSION_ENDED_REASON}`;
}

export function sessionEndedNotice(search) {
  return new URLSearchParams(search ?? '').get('reason') === SESSION_ENDED_REASON
    ? 'Your session has ended. Please sign in again.'
    : '';
}
