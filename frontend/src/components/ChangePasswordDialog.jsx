import React, { useState } from 'react';
import { api } from '../api/client';
import { apiErrorMessage } from '../lib/errors';
import Button from './ui/Button';
import { TextField } from './ui/Field';
import Modal from './ui/Modal';
import { ErrorNotice } from './ui/States';
import { useToast } from './ui/Toast';

const MIN_PASSWORD_LENGTH = 10;
const FORM_ID = 'change-password-form';

export default function ChangePasswordDialog({ onClose }) {
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const toast = useToast();

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
      toast.success('Password changed. Other devices have been signed out.');
      onClose();
    } catch (requestError) {
      setError(apiErrorMessage(requestError, 'Could not change the password. Please try again.'));
      setSaving(false);
    }
  };

  return (
    <Modal
      title="Change Password"
      size="sm"
      busy={saving}
      onClose={onClose}
      footer={(
        <>
          <Button variant="ghost" onClick={onClose} disabled={saving}>Cancel</Button>
          <Button type="submit" form={FORM_ID} disabled={saving}>{saving ? 'Saving…' : 'Change Password'}</Button>
        </>
      )}
    >
      <ErrorNotice>{error}</ErrorNotice>
      <form id={FORM_ID} onSubmit={handleSubmit} className="space-y-4">
        <TextField label="Current password" type="password" required autoComplete="current-password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} />
        <TextField label="New password" type="password" required autoComplete="new-password" hint={`At least ${MIN_PASSWORD_LENGTH} characters.`} value={newPassword} onChange={(event) => setNewPassword(event.target.value)} />
        <TextField label="Confirm new password" type="password" required autoComplete="new-password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} />
      </form>
    </Modal>
  );
}
