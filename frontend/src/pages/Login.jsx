import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, School } from 'lucide-react';
import { api } from '../api/client';
import Button from '../components/ui/Button';
import { TextField } from '../components/ui/Field';
import { ErrorNotice } from '../components/ui/States';
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
    <div className="flex min-h-screen items-center justify-center bg-navy-900 p-4">
      <main className="w-full max-w-md rounded-2xl bg-white p-8 shadow-2xl">
        <div className="mb-6 text-center">
          <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-600">
            <School className="h-8 w-8 text-white" aria-hidden="true" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-navy-900">EduCore AI</h1>
          <p className="mt-1 text-sm font-medium text-accent-700">Simple School Management, Smarter Decisions</p>
        </div>

        <form onSubmit={handleLogin} className="space-y-4">
          <ErrorNotice>{error}</ErrorNotice>
          <TextField label="Username" value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" required />
          <TextField label="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required />
          <Button type="submit" disabled={loading} className="w-full">
            <span>{loading ? 'Signing in…' : 'Sign In'}</span>
            {!loading && <ArrowRight className="h-4 w-4" aria-hidden="true" />}
          </Button>
        </form>
      </main>
    </div>
  );
}
