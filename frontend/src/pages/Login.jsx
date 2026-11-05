import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { School, Lock, User, ArrowRight, AlertCircle } from 'lucide-react';
import { api } from '../api/client';
import { apiErrorMessage } from '../lib/errors';

export default function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e?.preventDefault();
    setError('');
    setLoading(true);

    try {
      const res = await api.login(username, password);
      if (res.data.access_token) {
        localStorage.setItem('educore_token', res.data.access_token);
      }
      localStorage.setItem('educore_user', JSON.stringify({
        username: res.data.username,
        role: res.data.role
      }));
      navigate('/dashboard');
    } catch (err) {
      setError(apiErrorMessage(err, 'Could not sign in. Please check your details and try again.'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-950 to-slate-900 flex items-center justify-center p-4">
      <div className="max-w-md w-full">
        {/* Card */}
        <div className="bg-white rounded-2xl shadow-2xl p-8 border border-slate-100">
          {/* Header */}
          <div className="text-center mb-6">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-blue-700 to-indigo-600 mx-auto flex items-center justify-center shadow-lg shadow-blue-500/30 mb-3">
              <School className="w-9 h-9 text-white" />
            </div>
            <h1 className="text-2xl font-black text-slate-900 tracking-tight">AL-NOOR ACADEMY</h1>
            <p className="text-xs font-semibold uppercase tracking-wider text-blue-600 mt-1">
              EduCore AI Management Portal
            </p>
            <p className="text-xs text-slate-500 mt-1">Sign in with administrative credentials</p>
          </div>

          {error && (
            <div className="mb-5 p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
              <span>{error}</span>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                Username
              </label>
              <div className="relative">
                <User className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  autoComplete="username"
                  aria-label="Username"
                  required
                  className="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:bg-white transition-all"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                Password
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                  aria-label="Password"
                  required
                  className="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:bg-white transition-all"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white font-bold text-sm rounded-xl shadow-md hover:shadow-lg transition-all flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {loading ? (
                <span>Verifying Authentication...</span>
              ) : (
                <>
                  <span>Sign In to Dashboard</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

        </div>
      </div>
    </div>
  );
}
