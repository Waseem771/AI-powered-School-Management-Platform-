/**
 * Which screens each kind of account sees. This only decides what the app shows and where it sends
 * people. The backend refuses every request a role may not make, whatever this file says.
 */
export const STAFF_HOME = '/dashboard';
export const TEACHER_HOME = '/teacher/dashboard';
export const PARENT_HOME = '/parent/dashboard';
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
// Only the administrator account manages teachers, their classes and school-wide attendance.
const ADMIN_NAV = [
  { to: '/teachers', label: 'Teachers', icon: 'teachers' },
  { to: '/teacher-assignments', label: 'Teacher Assignments', icon: 'assignments' },
  { to: '/attendance', label: 'Attendance', icon: 'attendance' },
  { to: '/parents', label: 'Parents', icon: 'parents' },
];
const ADMIN_ONLY_SEGMENTS = new Set(['teachers', 'teacher-assignments', 'attendance', 'parents']);
const TEACHER_NAV = [
  { to: '/teacher/dashboard', label: 'Teacher Dashboard', icon: 'dashboard' },
  { to: '/teacher/classes', label: 'My Classes', icon: 'classes' },
  { to: '/teacher/profile', label: 'My Profile', icon: 'profile' },
];
const PARENT_NAV = [
  { to: '/parent/dashboard', label: 'Dashboard', icon: 'dashboard' },
  { to: '/parent/attendance', label: 'Attendance', icon: 'attendance' },
  { to: '/parent/results', label: 'Results', icon: 'results' },
  { to: '/parent/fees', label: 'Fees', icon: 'fees' },
  { to: '/parent/profile', label: 'My Profile', icon: 'profile' },
];

const roleOf = (user) => String(user?.role ?? '').toLowerCase();

export function isTeacher(user) {
  return roleOf(user) === 'teacher';
}

export function isParent(user) {
  return roleOf(user) === 'parent';
}

/** Teachers and parents have a portal of their own and see no staff screen. */
export function isPortalUser(user) {
  return isTeacher(user) || isParent(user);
}

/** The demo account sees the administrator's screens; the server refuses every change it tries. */
export function isAdmin(user) {
  return ['admin', 'demo'].includes(roleOf(user));
}

export function homePathFor(user) {
  if (isParent(user)) return PARENT_HOME;
  return isTeacher(user) ? TEACHER_HOME : STAFF_HOME;
}

export function navItemsFor(user) {
  if (isTeacher(user)) return TEACHER_NAV;
  if (isParent(user)) return PARENT_NAV;
  return isAdmin(user) ? [...STAFF_NAV, ...ADMIN_NAV] : STAFF_NAV;
}

/** True when this account has a screen at `pathname`. Whole path segments are compared, so "/teachers" is not "/teacher", and "/parents" is not "/parent". */
export function canAccessPath(user, pathname) {
  const firstSegment = String(pathname ?? '').split('/').filter(Boolean)[0] ?? '';
  if (isTeacher(user)) return firstSegment === 'teacher';
  if (isParent(user)) return firstSegment === 'parent';
  if (firstSegment === 'teacher' || firstSegment === 'parent') return false;
  if (ADMIN_ONLY_SEGMENTS.has(firstSegment)) return isAdmin(user);
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
