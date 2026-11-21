import React, { useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { KeyRound } from 'lucide-react';
import { api } from '../api/client';
import Button from '../components/ui/Button';
import { TextField } from '../components/ui/Field';
import { ErrorNotice, LoadingState } from '../components/ui/States';
import { apiErrorMessage } from '../lib/errors';
import { MIN_PASSWORD_LENGTH, newPasswordProblem, readResetToken } from '../lib/passwordReset';

/** Where the emailed link leads: /reset-password#token=... The token is read once, then removed from the address bar. */
export default function ResetPassword() {
  const location = useLocation();
  const [token] = useState(() => readResetToken(location.hash));
  const [status, setStatus] = useState(token ? 'checking' : 'invalid'); // checking, ready, invalid, done
  const [password, setPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    // Keeps the token out of browser history and out of anything that copies the address.
    if (location.hash) window.history.replaceState(null, '', window.location.pathname);
  }, [location.hash]);

  useEffect(() => {
    if (!token) return undefined;
    let cancelled = false;
    api.checkResetLink(token)
      .then(() => { if (!cancelled) setStatus('ready'); })
      .catch(() => { if (!cancelled) setStatus('invalid'); });
    return () => { cancelled = true; };
  }, [token]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    const problem = newPasswordProblem(password, confirmation);
    if (problem) {
      setError(problem);
      return;
    }
    setSaving(true);
    try {
      await api.resetPasswordWithLink(token, password);
      setStatus('done');
    } catch (requestError) {
      if (requestError.response?.status === 400) setStatus('invalid'); // spent or expired while the page was open
      else setError(apiErrorMessage(requestError, 'Could not change the password. Please try again.'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-navy-900 p-4">
      <main className="w-full max-w-md rounded-2xl bg-white p-8 shadow-2xl">
        <div className="mb-6 text-center">
          <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-600">
            <KeyRound className="h-8 w-8 text-white" aria-hidden="true" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-navy-900">Choose a new password</h1>
        </div>

        {status === 'checking' && <LoadingState label="Checking your link…" />}

        {status === 'invalid' && (
          <div className="space-y-4">
            <p role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-900">
              This reset link is not valid any more. It may have expired or already been used.
            </p>
            <Link to="/forgot-password" className="block text-center text-sm font-semibold text-brand-700 underline">Ask for a new link</Link>
            <Link to="/login" className="block text-center text-sm font-semibold text-brand-700 underline">Back to sign in</Link>
          </div>
        )}

        {status === 'ready' && (
          <form onSubmit={handleSubmit} noValidate className="space-y-4">
            <ErrorNotice>{error}</ErrorNotice>
            <TextField label="New password" type="password" hint={`At least ${MIN_PASSWORD_LENGTH} characters.`} value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="new-password" />
            <TextField label="Confirm new password" type="password" value={confirmation} onChange={(e) => setConfirmation(e.target.value)} autoComplete="new-password" />
            <Button type="submit" disabled={saving} className="w-full">{saving ? 'Saving…' : 'Change Password'}</Button>
            <p className="text-center text-xs text-slate-600">You will be signed out everywhere and asked to sign in again.</p>
          </form>
        )}

        {status === 'done' && (
          <div className="space-y-4">
            <p role="status" className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-900">
              Your password has been changed. Please sign in with the new password.
            </p>
            <Link to="/login" className="block rounded-xl bg-brand-600 px-4 py-3 text-center text-sm font-semibold text-white">Go to sign in</Link>
          </div>
        )}
      </main>
    </div>
  );
}
