import React, { useState } from 'react';
import Button from './ui/Button';
import Modal from './ui/Modal';
import { ErrorNotice } from './ui/States';
import { apiErrorMessage } from '../lib/errors';

export default function DeleteAccountDialog({ name, remove, onClose, onDone }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const confirmDelete = async () => {
    setBusy(true);
    setError('');
    try {
      await remove();
      onDone(name);
    } catch (requestError) {
      setError(apiErrorMessage(requestError, 'Could not delete the account. Please try again.'));
      setBusy(false);
    }
  };

  return (
    <Modal
      title="Delete account?"
      size="sm"
      busy={busy}
      onClose={onClose}
      footer={(
        <>
          <Button variant="ghost" onClick={onClose} disabled={busy}>Cancel</Button>
          <Button variant="danger" onClick={confirmDelete} disabled={busy}>{busy ? 'Deleting…' : 'Delete account'}</Button>
        </>
      )}
    >
      <ErrorNotice>{error}</ErrorNotice>
      <p className="text-sm text-slate-700">
        {name}&apos;s sign-in and its links to classes or children will be removed. This cannot be undone.
      </p>
    </Modal>
  );
}
