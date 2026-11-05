import React, { useEffect, useRef, useState } from 'react';
import { AlertCircle, CheckCircle2, X } from 'lucide-react';
import { api } from '../api/client';
import { apiErrorMessage } from '../lib/errors';

const MIN_PASSWORD_LENGTH = 10;
const SUCCESS_CLOSE_DELAY_MS = 1200;
const INPUT_CLASS =
  'w-full px-3 py-2 text-sm bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-600 focus:bg-white';

function PasswordField({ id, label, value, onChange, autoComplete, inputRef, hint }) {
  return (
    <div>
      <label htmlFor={id} className="block text-xs font-bold text-slate-700 mb-1">{label}</label>
      <input
        id={id}
        ref={inputRef}
        type="password"
        required
        value={value}
        autoComplete={autoComplete}
        onChange={(event) => onChange(event.target.value)}
        className={INPUT_CLASS}
      />
      {hint && <p className="text-[11px] text-slate-500 mt-1">{hint}</p>}
    </div>
  );
}

export default function ChangePasswordDialog({ onClose }) {
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const firstFieldRef = useRef(null);

  useEffect(() => {
    firstFieldRef.current?.focus();
    const closeOnEscape = (event) => {
      if (event.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', closeOnEscape);
    return () => window.removeEventListener('keydown', closeOnEscape);
  }, [onClose]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');

    if (newPassword.length < MIN_PASSWORD_LENGTH) {
      setError(`New password must be at least ${MIN_PASSWORD_LENGTH} characters.`);
      return;
    }
    if (newPassword !== confirmPassword) {
      setError('The two new passwords do not match.');
      return;
    }

    setSaving(true);
    try {
      const response = await api.changePassword(currentPassword, newPassword);
      // Older sessions have just ended, including this one's previous token.
      localStorage.setItem('educore_token', response.data.access_token);
      setSaved(true);
      setTimeout(onClose, SUCCESS_CLOSE_DELAY_MS);
    } catch (requestError) {
      setError(apiErrorMessage(requestError, 'Could not change the password. Please try again.'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/60 flex items-center justify-center p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="change-password-title"
        className="bg-white rounded-2xl max-w-sm w-full p-6 shadow-2xl border border-slate-100"
      >
        <div className="flex items-center justify-between pb-3 border-b border-slate-100 mb-4">
          <h3 id="change-password-title" className="text-base font-bold text-slate-900">Change Password</h3>
          <button type="button" onClick={onClose} aria-label="Close" className="min-h-11 min-w-11 flex items-center justify-center text-slate-400 hover:text-slate-600">
            <X className="w-5 h-5" />
          </button>
        </div>

        {error && (
          <div role="alert" className="mb-4 p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {saved ? (
          <div role="status" className="p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-sm flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>Password changed. Other devices have been signed out.</span>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <PasswordField id="current-password" label="Current password" value={currentPassword} onChange={setCurrentPassword} autoComplete="current-password" inputRef={firstFieldRef} />
            <PasswordField id="new-password" label="New password" value={newPassword} onChange={setNewPassword} autoComplete="new-password" hint={`At least ${MIN_PASSWORD_LENGTH} characters.`} />
            <PasswordField id="confirm-password" label="Confirm new password" value={confirmPassword} onChange={setConfirmPassword} autoComplete="new-password" />

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
              <button type="button" onClick={onClose} className="min-h-11 px-4 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-xl">
                Cancel
              </button>
              <button type="submit" disabled={saving} className="min-h-11 px-5 text-xs font-bold text-white bg-blue-600 hover:bg-blue-700 rounded-xl disabled:opacity-60">
                {saving ? 'Saving…' : 'Change Password'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
