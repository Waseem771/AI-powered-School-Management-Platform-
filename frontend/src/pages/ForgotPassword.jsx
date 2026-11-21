import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { MailCheck } from 'lucide-react';
import { api } from '../api/client';
import Button from '../components/ui/Button';
import { TextField } from '../components/ui/Field';
import { ErrorNotice } from '../components/ui/States';
import { apiErrorMessage } from '../lib/errors';
import { looksLikeEmail } from '../lib/passwordReset';

/**
 * Teachers and parents ask for a reset link by email. The answer is the same whether or not the address belongs
 * to an account, so this page can never be used to find out who has one.
 */
export default function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [sent, setSent] = useState(false);
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    if (!looksLikeEmail(email)) {
      setError('Enter the email address the school office has on file for you.');
      return;
    }
    setSaving(true);
    try {
      await api.forgotPassword(email.trim());
      setSent(true);
    } catch (requestError) {
      setError(apiErrorMessage(requestError, 'Could not send the request. Please try again.'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-navy-900 p-4">
      <main className="w-full max-w-md rounded-2xl bg-white p-8 shadow-2xl">
        <div className="mb-6 text-center">
          <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-600">
            <MailCheck className="h-8 w-8 text-white" aria-hidden="true" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-navy-900">Forgot your password?</h1>
          <p className="mt-2 text-sm text-slate-600">
            Teachers and parents can reset it here. Enter the email address the school office has on file.
          </p>
        </div>

        {sent ? (
          <div className="space-y-4">
            <p role="status" className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-900">
              If that email address belongs to a teacher or parent account, a reset link is on its way. It works once,
              for 60 minutes. Check your spam folder if you do not see it.
            </p>
            <p className="text-sm text-slate-600">
              No email arrived, or no email is on file for you? Ask the school office to reset your password.
            </p>
            <Link to="/login" className="block text-center text-sm font-semibold text-brand-700 underline">Back to sign in</Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit} noValidate className="space-y-4">
            <ErrorNotice>{error}</ErrorNotice>
            <TextField label="Email address" type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" />
            <Button type="submit" disabled={saving} className="w-full">{saving ? 'Sending…' : 'Send reset link'}</Button>
            <Link to="/login" className="block text-center text-sm font-semibold text-brand-700 underline">Back to sign in</Link>
            <p className="text-center text-xs text-slate-600">Administrators cannot reset a password here.</p>
          </form>
        )}
      </main>
    </div>
  );
}
