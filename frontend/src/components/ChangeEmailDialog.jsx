import React, { useState } from 'react';
import { apiErrorMessage } from '../lib/errors';
import { looksLikeEmail } from '../lib/passwordReset';
import Button from './ui/Button';
import { TextField } from './ui/Field';
import Modal from './ui/Modal';
import { ErrorNotice } from './ui/States';

const FORM_ID = 'change-email-form';

/**
 * The administrator's dialog for the email address a teacher or parent resets their own password with.
 * That address decides who can take over the account, so the administrator confirms with their own password.
 * `save(email, adminPassword)` makes the request, so teachers and parents share one dialog.
 */
export default function ChangeEmailDialog({ name, current, save, onClose, onDone }) {
  const [email, setEmail] = useState(current || '');
  const [adminPassword, setAdminPassword] = useState('');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    const trimmed = email.trim();
    if (trimmed && !looksLikeEmail(trimmed)) {
      setError('Enter one valid email address (no commas or lists), or leave it empty to remove it.');
      return;
    }
    if (!adminPassword) {
      setError('Enter your own administrator password to confirm.');
      return;
    }
    setSaving(true);
    try {
      await save(trimmed || null, adminPassword);
      onDone(name, Boolean(trimmed));
    } catch (requestError) {
      setError(apiErrorMessage(requestError, 'Could not change the email address. Please try again.'));
      setSaving(false);
    }
  };

  return (
    <Modal
      title={`Email address for ${name}`}
      description="This is where a password reset link is sent. Only enter an address the person owns."
      busy={saving}
      onClose={onClose}
      footer={(
        <>
          <Button variant="ghost" onClick={onClose} disabled={saving}>Cancel</Button>
          <Button type="submit" form={FORM_ID} disabled={saving}>{saving ? 'Saving…' : 'Save Email'}</Button>
        </>
      )}
    >
      <ErrorNotice>{error}</ErrorNotice>
      <p className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
        Check with the person first. Any reset link already sent is cancelled, and the old address is told about the change.
      </p>
      <form id={FORM_ID} onSubmit={handleSubmit} noValidate className="mt-4 space-y-4">
        <TextField label="Email address" type="email" hint="Leave empty to remove it. Without an email, only you can reset their password." value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="off" />
        <TextField label="Your administrator password" type="password" value={adminPassword} onChange={(event) => setAdminPassword(event.target.value)} autoComplete="current-password" />
      </form>
    </Modal>
  );
}
