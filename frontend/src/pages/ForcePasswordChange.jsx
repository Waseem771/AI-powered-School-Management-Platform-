import React, { useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import { KeyRound } from 'lucide-react';
import { api } from '../api/client';
import Button from '../components/ui/Button';
import { TextField } from '../components/ui/Field';
import { ErrorNotice } from '../components/ui/States';
import { homePathFor } from '../lib/access';
import { apiErrorMessage } from '../lib/errors';
import { clearSession, getStoredUser, mustChangePassword, setPasswordChangeRequired } from '../lib/session';

const MIN_PASSWORD_LENGTH = 10;

/** Shown after an administrator reset the password. Nothing else opens until the owner chooses their own. */
export default function ForcePasswordChange() {
  const navigate = useNavigate();
  const user = getStoredUser();
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  if (!localStorage.getItem('educore_token')) return <Navigate to="/login" replace />;
  if (!mustChangePassword(user)) return <Navigate to={homePathFor(user)} replace />;

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    if (!currentPassword) {
      setError('Enter the temporary password the school office gave you.');
      return;
    }
    if (newPassword.length < MIN_PASSWORD_LENGTH) {
      setError(`Your new password must be at least ${MIN_PASSWORD_LENGTH} characters.`);
      return;
    }
    if (newPassword !== confirmPassword) {
      setError('The two new passwords do not match.');
      return;
    }
    setSaving(true);
    try {
      const response = await api.changePassword(currentPassword, newPassword);
      localStorage.setItem('educore_token', response.data.access_token);
      setPasswordChangeRequired(false);
      navigate(homePathFor(user), { replace: true });
    } catch (requestError) {
      setError(apiErrorMessage(requestError, 'Could not change the password. Please try again.'));
      setSaving(false);
    }
  };

  const signOut = async () => {
    try {
      await api.logout();
    } catch (requestError) {
      console.warn('Logout request did not complete:', requestError);
    }
    clearSession();
    navigate('/login', { replace: true });
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-navy-900 p-4">
      <main className="w-full max-w-md rounded-2xl bg-white p-8 shadow-2xl">
        <div className="mb-6 text-center">
          <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-600">
            <KeyRound className="h-8 w-8 text-white" aria-hidden="true" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-navy-900">Choose a new password</h1>
          <p className="mt-2 text-sm text-slate-600">
            The school office reset your password. Enter the temporary password they gave you, then choose a password only you know.
          </p>
        </div>
        <form onSubmit={handleSubmit} noValidate className="space-y-4">
          <ErrorNotice>{error}</ErrorNotice>
          <TextField label="Temporary password" type="password" value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)} autoComplete="current-password" />
          <TextField label="New password" type="password" hint={`At least ${MIN_PASSWORD_LENGTH} characters.`} value={newPassword} onChange={(e) => setNewPassword(e.target.value)} autoComplete="new-password" />
          <TextField label="Confirm new password" type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} autoComplete="new-password" />
          <Button type="submit" disabled={saving} className="w-full">{saving ? 'Saving…' : 'Change Password'}</Button>
          <Button variant="ghost" onClick={signOut} disabled={saving} className="w-full">Sign out</Button>
        </form>
      </main>
    </div>
  );
}
