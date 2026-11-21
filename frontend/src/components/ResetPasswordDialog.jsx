import React, { useState } from 'react';
import { apiErrorMessage } from '../lib/errors';
import Button from './ui/Button';
import { TextField } from './ui/Field';
import Modal from './ui/Modal';
import { ErrorNotice } from './ui/States';

const MIN_PASSWORD_LENGTH = 10;
const FORM_ID = 'reset-password-form';

/**
 * The administrator's confirmation dialog for setting a new password on someone else's account.
 * `reset(password)` makes the request, so parents and teachers share one dialog. The password is never shown
 * again, and the person must choose their own at next sign-in.
 */
export default function ResetPasswordDialog({ name, kept, reset, onClose, onDone }) {
  const [password, setPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    if (password.length < MIN_PASSWORD_LENGTH) {
      setError(`The password must be at least ${MIN_PASSWORD_LENGTH} characters.`);
      return;
    }
    if (password !== confirmation) {
      setError('The two passwords do not match.');
      return;
    }
    setSaving(true);
    try {
      await reset(password);
      onDone(name);
    } catch (requestError) {
      setError(apiErrorMessage(requestError, 'Could not reset the password. Please try again.'));
      setSaving(false);
    }
  };

  return (
    <Modal
      title={`Reset password for ${name}?`}
      description="Share the new password privately. It is not shown again."
      busy={saving}
      onClose={onClose}
      footer={(
        <>
          <Button variant="ghost" onClick={onClose} disabled={saving}>Cancel</Button>
          <Button type="submit" form={FORM_ID} variant="danger" disabled={saving}>{saving ? 'Saving…' : 'Reset Password'}</Button>
        </>
      )}
    >
      <ErrorNotice>{error}</ErrorNotice>
      <p className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
        {name} will be signed out everywhere at once, and must choose a new password the next time they sign in.
        {kept ? ` ${kept}` : ''}
      </p>
      <form id={FORM_ID} onSubmit={handleSubmit} noValidate className="mt-4 space-y-4">
        <TextField label="New temporary password" type="password" hint={`At least ${MIN_PASSWORD_LENGTH} characters.`} value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="new-password" />
        <TextField label="Confirm the password" type="password" value={confirmation} onChange={(event) => setConfirmation(event.target.value)} autoComplete="new-password" />
      </form>
    </Modal>
  );
}
