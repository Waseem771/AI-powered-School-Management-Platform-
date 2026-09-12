import React, { useState } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  Users,
  Receipt,
  GraduationCap,
  AlertTriangle,
  Bot,
  LogOut,
  School,
  Menu,
  X,
  Sparkles,
  ShieldCheck
} from 'lucide-react';

export default function Layout() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const navigate = useNavigate();
  const user = JSON.parse(localStorage.getItem('educore_user') || '{"username":"admin","role":"admin"}');

  const handleLogout = () => {
    localStorage.removeItem('educore_token');
    localStorage.removeItem('educore_user');
    navigate('/login');
  };

  const navItems = [
    { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/students', label: 'Students', icon: Users },
    { to: '/fees', label: 'Fee Management', icon: Receipt },
    { to: '/results', label: 'Exam Results', icon: GraduationCap },
    {
      to: '/at-risk',
      label: 'AI At-Risk Prediction',
      icon: AlertTriangle,
      badge: 'SHAP AI',
      badgeColor: 'bg-rose-100 text-rose-700 border-rose-200'
    },
    {
      to: '/chatbot',
      label: 'Policy Chatbot',
      icon: Bot,
      badge: 'RAG',
      badgeColor: 'bg-indigo-100 text-indigo-700 border-indigo-200'
    },
  ];

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col md:flex-row">
      {/* Mobile Top Bar */}
      <div className="md:hidden bg-slate-900 text-white px-4 py-3 flex items-center justify-between shadow-md">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center font-bold text-white text-sm">
            AN
          </div>
          <div>
            <h1 className="font-bold text-sm tracking-wide text-white">Al-Noor Academy</h1>
            <p className="text-[10px] text-blue-300 font-medium">EduCore AI Platform</p>
          </div>
        </div>
        <button
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="p-1.5 rounded-lg text-slate-300 hover:text-white hover:bg-slate-800"
        >
          {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
        </button>
      </div>

      {/* Sidebar */}
      <aside
        className={`fixed md:sticky top-0 h-screen z-40 bg-slate-900 text-white w-64 flex flex-col justify-between transition-transform duration-200 ease-in-out border-r border-slate-800 ${
          mobileMenuOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
        }`}
      >
        <div>
          {/* Logo & School Header */}
          <div className="p-5 border-b border-slate-800 flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center shadow-md">
              <School className="w-6 h-6 text-white" />
            </div>
            <div>
              <h2 className="font-bold text-base leading-tight text-white">Al-Noor Academy</h2>
              <div className="flex items-center gap-1 mt-0.5">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                <span className="text-[11px] text-slate-400 font-medium">EduCore AI &bull; Active</span>
              </div>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="p-3 space-y-1.5 mt-2">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  onClick={() => setMobileMenuOpen(false)}
                  className={({ isActive }) =>
                    `flex items-center justify-between px-3.5 py-2.5 rounded-xl font-medium text-sm transition-colors ${
                      isActive
                        ? 'bg-blue-600 text-white shadow-sm'
                        : 'text-slate-300 hover:bg-slate-800/80 hover:text-white'
                    }`
                  }
                >
                  <div className="flex items-center gap-3">
                    <Icon className="w-4 h-4 shrink-0" />
                    <span>{item.label}</span>
                  </div>
                  {item.badge && (
                    <span
                      className={`text-[10px] px-1.5 py-0.5 rounded-md font-semibold border ${item.badgeColor}`}
                    >
                      {item.badge}
                    </span>
                  )}
                </NavLink>
              );
            })}
          </nav>
        </div>

        {/* User Profile & Logout */}
        <div className="p-4 border-t border-slate-800">
          <div className="bg-slate-800/60 rounded-xl p-3 flex items-center justify-between mb-3 border border-slate-700/50">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-indigo-600 text-white font-bold flex items-center justify-center text-xs">
                {user.username?.charAt(0).toUpperCase() || 'A'}
              </div>
              <div className="truncate">
                <p className="text-xs font-semibold text-white capitalize">{user.username}</p>
                <p className="text-[10px] text-slate-400 flex items-center gap-1">
                  <ShieldCheck className="w-3 h-3 text-emerald-400" />
                  <span>Administrator</span>
                </p>
              </div>
            </div>
          </div>

          <button
            onClick={handleLogout}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-xl text-xs font-semibold text-rose-400 hover:bg-rose-950/40 hover:text-rose-300 transition-colors border border-rose-900/30"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span>Sign Out</span>
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Navbar */}
        <header className="hidden md:flex bg-white border-b border-slate-200/80 px-8 py-3.5 items-center justify-between sticky top-0 z-30 shadow-xs">
          <div>
            <span className="text-xs font-semibold text-blue-700 bg-blue-50 px-2.5 py-1 rounded-full border border-blue-200">
              Academic Session 2025-2026
            </span>
          </div>
          <div className="flex items-center gap-4 text-xs text-slate-600">
            <div className="flex items-center gap-1.5 bg-slate-100 px-3 py-1.5 rounded-lg border border-slate-200">
              <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
              <span className="font-semibold text-slate-700">AI Stack Active:</span>
              <span>scikit-learn &bull; SHAP &bull; FAISS &bull; Groq</span>
            </div>
            <span className="text-slate-400">|</span>
            <span className="font-medium text-slate-700">Logged in as: <b>{user.username}</b></span>
          </div>
        </header>

        {/* Page Views Container */}
        <main className="flex-1 p-4 md:p-8 max-w-7xl w-full mx-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
