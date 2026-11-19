import assert from 'node:assert/strict';
import test from 'node:test';

import {
  canAccessPath,
  homePathFor,
  isAdmin,
  isTeacher,
  navItemsFor,
  sessionEndedNotice,
  sessionEndedPath,
} from './access.js';

const admin = { username: 'admin', role: 'admin' };
const registrar = { username: 'r', role: 'Registrar' };
const teacher = { username: 'sara', role: 'teacher' };

test('each role lands on its own home screen', () => {
  assert.equal(homePathFor(admin), '/dashboard');
  assert.equal(homePathFor(registrar), '/dashboard');
  assert.equal(homePathFor(teacher), '/teacher/dashboard');
  assert.equal(homePathFor(null), '/dashboard');
});

test('roles are recognised whatever their capitalisation', () => {
  assert.equal(isTeacher({ role: 'Teacher' }), true);
  assert.equal(isTeacher(admin), false);
  assert.equal(isAdmin({ role: 'ADMIN' }), true);
  assert.equal(isAdmin(registrar), false);
});

test('a teacher sees only the teacher menu, and no administrative item', () => {
  const items = navItemsFor(teacher);

  assert.deepEqual(items.map((item) => item.to), ['/teacher/dashboard', '/teacher/classes', '/teacher/profile']);
  for (const restricted of ['/students', '/fees', '/admissions', '/teachers', '/chatbot', '/attendance', '/teacher-assignments']) {
    assert.equal(items.some((item) => item.to === restricted), false, restricted);
  }
});

test('an administrator keeps every existing item and gains Teachers; other staff do not get it', () => {
  const adminLinks = navItemsFor(admin).map((item) => item.to);

  assert.deepEqual(adminLinks.slice(0, 7), [
    '/dashboard', '/students', '/fees', '/results', '/at-risk', '/chatbot', '/admissions',
  ]);
  assert.deepEqual(adminLinks.slice(7), ['/teachers', '/teacher-assignments', '/attendance']);
  for (const adminOnly of ['/teachers', '/teacher-assignments', '/attendance']) {
    assert.equal(navItemsFor(registrar).some((item) => item.to === adminOnly), false, adminOnly);
  }
  assert.equal(navItemsFor(admin).some((item) => item.to.startsWith('/teacher/')), false);
});

test('a teacher is sent away from every restricted screen, including by direct address', () => {
  for (const path of ['/dashboard', '/students', '/students/4', '/fees', '/results', '/at-risk', '/chatbot',
    '/admissions', '/admissions/new', '/teachers', '/attendance', '/attendance/report', '/teacher-assignments', '/']) {
    assert.equal(canAccessPath(teacher, path), false, path);
  }
  assert.equal(canAccessPath(teacher, '/teacher/classes/4/attendance'), true);
  assert.equal(canAccessPath(teacher, '/teacher/dashboard'), true);
  assert.equal(canAccessPath(teacher, '/teacher/profile'), true);
});

test('staff cannot open the teacher portal, and only an administrator manages teachers', () => {
  assert.equal(canAccessPath(admin, '/teacher/dashboard'), false);
  assert.equal(canAccessPath(registrar, '/teacher/profile'), false);
  assert.equal(canAccessPath(admin, '/teachers'), true);
  assert.equal(canAccessPath(registrar, '/teachers'), false);
  for (const path of ['/attendance', '/attendance/report', '/teacher-assignments']) {
    assert.equal(canAccessPath(admin, path), true, path);
    assert.equal(canAccessPath(registrar, path), false, path);
  }
  assert.equal(canAccessPath(registrar, '/students'), true);
  assert.equal(canAccessPath(admin, '/admissions/3/edit'), true);
});

test('the sign-in page explains an ended session, such as a deactivated account', () => {
  assert.equal(sessionEndedPath(), '/login?reason=ended');
  assert.equal(sessionEndedNotice('?reason=ended'), 'Your session has ended. Please sign in again.');
  assert.equal(sessionEndedNotice(''), '');
  assert.equal(sessionEndedNotice('?reason=other'), '');
});
