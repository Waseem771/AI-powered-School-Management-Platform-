import React, { useEffect, useRef, useState } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import {
  AlertTriangle,
  Bot,
  ClipboardCheck,
  GraduationCap,
  KeyRound,
  LayoutDashboard,
  LogOut,
  Menu,
  Receipt,
  School,
  Users,
  X,
} from 'lucide-react';
import { clearSession, getStoredUser } from '../lib/session';
import { roleLabel, sessionLabel } from '../lib/schoolInfo';
import { api } from '../api/client';
import ChangePasswordDialog from './ChangePasswordDialog';

const NAV_ITEMS = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/students', label: 'Students', icon: Users },
  { to: '/fees', label: 'Fees', icon: Receipt },
  { to: '/results', label: 'Exam Results', icon: GraduationCap },
  { to: '/at-risk', label: 'Academic Early Warning', icon: AlertTriangle },
  { to: '/chatbot', label: 'School Assistant', icon: Bot },
  { to: '/admissions', label: 'Admissions', icon: ClipboardCheck },
];

export default function Layout() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [changingPassword, setChangingPassword] = useState(false);
  const [school, setSchool] = useState(null);
  const menuButtonRef = useRef(null);
  const drawerRef = useRef(null);
  const navigate = useNavigate();
  const user = getStoredUser();

  useEffect(() => {
    const controller = new AbortController();
    api.getSchoolInfo({ signal: controller.signal })
      .then((res) => setSchool(res.data))
      .catch((error) => {
        // The header simply leaves out the school's details. Every page reports its own failures.
        if (error.code !== 'ERR_CANCELED') console.warn('School details did not load:', error);
      });
    return () => controller.abort();
  }, []);

  const handleLogout = async () => {
    try {
      await api.logout();
    } catch (error) {
      console.warn('Logout request did not complete:', error);
    }
    clearSession();
    navigate('/login');
  };

  useEffect(() => {
    if (!mobileMenuOpen) return undefined;

    const firstNavigationItem = drawerRef.current?.querySelector('a');
    firstNavigationItem?.focus();

    const closeOnEscape = (event) => {
      if (event.key === 'Escape') {
        setMobileMenuOpen(false);
        menuButtonRef.current?.focus();
      }
    };

    window.addEventListener('keydown', closeOnEscape);
    return () => window.removeEventListener('keydown', closeOnEscape);
  }, [mobileMenuOpen]);

  const trapDrawerFocus = (event) => {
    if (event.key !== 'Tab' || !mobileMenuOpen) return;
    const focusableElements = drawerRef.current?.querySelectorAll('a, button:not([disabled])');
    if (!focusableElements?.length) return;
    const first = focusableElements[0];
    const last = focusableElements[focusableElements.length - 1];

    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  };

  const schoolName = school?.name ?? 'EduCore AI';
  const session = sessionLabel(school);

  return (
    <div className="flex min-h-screen flex-col bg-slate-50 md:flex-row">
      {/* Mobile top bar */}
      <div className="flex items-center justify-between bg-navy-900 px-4 py-2 text-white md:hidden">
        <div className="flex min-w-0 items-center gap-2">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-brand-600">
            <School className="h-5 w-5 text-white" aria-hidden="true" />
          </div>
          <div className="min-w-0">
            <p className="truncate text-sm font-bold text-white">{schoolName}</p>
            {session && <p className="truncate text-[11px] text-accent-300">{session}{school?.demo_mode ? ' · DEMO MODE' : ''}</p>}
          </div>
        </div>
        <button
          ref={menuButtonRef}
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="flex min-h-11 min-w-11 items-center justify-center rounded-lg text-slate-200 hover:bg-navy-700 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white"
          aria-label={mobileMenuOpen ? 'Close navigation menu' : 'Open navigation menu'}
          aria-expanded={mobileMenuOpen}
          aria-controls="primary-navigation"
        >
          {mobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
        </button>
      </div>

      {mobileMenuOpen && (
        <button
          type="button"
          className="fixed inset-0 z-30 bg-navy-950/50 md:hidden"
          aria-label="Close navigation menu"
          onClick={() => setMobileMenuOpen(false)}
        />
      )}

      {/* Sidebar. It is only a dialog while it covers the page on a phone. */}
      <aside
        ref={drawerRef}
        role={mobileMenuOpen ? 'dialog' : undefined}
        aria-modal={mobileMenuOpen || undefined}
        aria-label="Main navigation"
        onKeyDown={trapDrawerFocus}
        className={`fixed top-0 z-40 flex h-[100dvh] w-64 flex-col justify-between overflow-y-auto bg-navy-900 text-white transition-transform duration-200 ease-in-out md:sticky ${
          mobileMenuOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
        }`}
      >
        <div>
          <div className="flex items-center gap-3 border-b border-navy-700 p-5">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand-600">
              <School className="h-6 w-6 text-white" aria-hidden="true" />
            </div>
            <div className="min-w-0">
              <p className="text-base font-bold leading-tight text-white">{schoolName}</p>
              <p className="mt-0.5 text-xs font-medium text-accent-300">EduCore AI</p>
            </div>
          </div>

          <nav id="primary-navigation" aria-label="Main navigation" className="mt-2 space-y-1 p-3">
            {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                onClick={() => setMobileMenuOpen(false)}
                className={({ isActive }) =>
                  `flex min-h-11 items-center gap-3 rounded-xl px-3.5 text-sm font-medium transition-colors ${
                    isActive ? 'bg-brand-600 text-white' : 'text-slate-200 hover:bg-navy-700 hover:text-white'
                  }`
                }
              >
                <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
                <span>{label}</span>
              </NavLink>
            ))}
          </nav>
        </div>

        <div className="space-y-2 border-t border-navy-700 p-4">
          <div className="flex items-center gap-2.5 px-1 pb-1">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-navy-600 text-xs font-bold text-white">
              {user.username?.charAt(0).toUpperCase()}
            </div>
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-white">{user.username}</p>
              <p className="text-xs text-slate-300">{roleLabel(user.role)}</p>
            </div>
          </div>
          <button
            onClick={() => { setMobileMenuOpen(false); setChangingPassword(true); }}
            className="flex min-h-11 w-full items-center justify-center gap-2 rounded-xl border border-navy-600 text-sm font-semibold text-slate-100 hover:bg-navy-700"
          >
            <KeyRound className="h-4 w-4" aria-hidden="true" />
            <span>Change Password</span>
          </button>
          <button
            onClick={handleLogout}
            className="flex min-h-11 w-full items-center justify-center gap-2 rounded-xl border border-navy-600 text-sm font-semibold text-slate-100 hover:bg-navy-700"
          >
            <LogOut className="h-4 w-4" aria-hidden="true" />
            <span>Sign Out</span>
          </button>
        </div>
      </aside>

      {changingPassword && <ChangePasswordDialog onClose={() => setChangingPassword(false)} />}

      <div className="flex min-w-0 flex-1 flex-col" inert={mobileMenuOpen ? '' : undefined} aria-hidden={mobileMenuOpen || undefined}>
        <header className="sticky top-0 z-30 hidden items-center justify-between border-b border-slate-200 bg-white px-8 py-3 md:flex">
          <div>
            {session && <span className="rounded-full border border-brand-200 bg-brand-50 px-2.5 py-1 text-xs font-semibold text-brand-800">{session}</span>}
            {school?.demo_mode && <span className="ml-2 rounded-full border border-amber-300 bg-amber-100 px-2.5 py-1 text-xs font-bold text-amber-900">DEMO MODE</span>}
          </div>
          <p className="text-sm text-slate-700">Signed in as <b>{user.username}</b></p>
        </header>

        <main id="main-content" className="mx-auto w-full max-w-7xl flex-1 p-4 md:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
