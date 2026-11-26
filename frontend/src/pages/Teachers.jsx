import React, { useState } from 'react';
import { useOutletContext } from 'react-router-dom';
import { UserPlus } from 'lucide-react';
import { api } from '../api/client';
import DataTable from '../components/DataTable';
import ChangeEmailDialog from '../components/ChangeEmailDialog';
import DeleteAccountDialog from '../components/DeleteAccountDialog';
import ResetPasswordDialog from '../components/ResetPasswordDialog';
import Button from '../components/ui/Button';
import { TextField } from '../components/ui/Field';
import Modal from '../components/ui/Modal';
import { Badge, Card, PageHeader } from '../components/ui/Page';
import { ErrorNotice } from '../components/ui/States';
import { useToast } from '../components/ui/Toast';
import { apiErrorMessage } from '../lib/errors';
import { useLoad } from '../lib/useLoad';

const MIN_PASSWORD_LENGTH = 10;
const FORM_ID = 'create-teacher-form';
const EMPTY_FORM = { full_name: '', username: '', email: '', password: '' };

function CreateTeacherDialog({ onClose, onCreated }) {
  const [form, setForm] = useState(EMPTY_FORM);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const set = (field) => (event) => setForm((current) => ({ ...current, [field]: event.target.value }));

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    if (!form.full_name.trim() || !form.username.trim()) {
      setError('Enter the teacher\'s full name and a username.');
      return;
    }
    if (form.password.length < MIN_PASSWORD_LENGTH) {
      setError(`The password must be at least ${MIN_PASSWORD_LENGTH} characters.`);
      return;
    }
    setSaving(true);
    try {
      await api.createTeacher({
        full_name: form.full_name.trim(),
        username: form.username.trim(),
        email: form.email.trim() || null,
        password: form.password,
      });
      onCreated(form.full_name.trim());
    } catch (requestError) {
      setError(apiErrorMessage(requestError, 'Could not create the account. Please try again.'));
      setSaving(false);
    }
  };

  return (
    <Modal
      title="Add Teacher"
      description="Creates a sign-in for a teacher. Share the password with them privately."
      busy={saving}
      onClose={onClose}
      footer={(
        <>
          <Button variant="ghost" onClick={onClose} disabled={saving}>Cancel</Button>
          <Button type="submit" form={FORM_ID} disabled={saving}>{saving ? 'Saving…' : 'Create Account'}</Button>
        </>
      )}
    >
      <ErrorNotice>{error}</ErrorNotice>
      <form id={FORM_ID} onSubmit={handleSubmit} noValidate className="space-y-4">
        <TextField label="Full name" value={form.full_name} onChange={set('full_name')} autoComplete="off" />
        <TextField label="Username" hint="3-50 letters, numbers, dots, dashes or underscores." value={form.username} onChange={set('username')} autoComplete="off" />
        <TextField label="Email (optional)" type="email" value={form.email} onChange={set('email')} autoComplete="off" />
        <TextField label="Initial password" type="password" hint={`At least ${MIN_PASSWORD_LENGTH} characters. The teacher can change it after signing in.`} value={form.password} onChange={set('password')} autoComplete="new-password" />
      </form>
    </Modal>
  );
}

function ConfirmDeactivate({ teacher, busy, onCancel, onConfirm }) {
  return (
    <Modal
      title="Deactivate account?"
      size="sm"
      busy={busy}
      onClose={onCancel}
      footer={(
        <>
          <Button variant="ghost" onClick={onCancel} disabled={busy}>Cancel</Button>
          <Button variant="danger" onClick={onConfirm} disabled={busy}>{busy ? 'Saving…' : 'Deactivate'}</Button>
        </>
      )}
    >
      <p className="text-sm text-slate-700">
        {teacher.full_name || teacher.username} will be signed out at once and will not be able to sign in
        until you activate the account again. Nothing is deleted.
      </p>
    </Modal>
  );
}

export default function Teachers() {
  const toast = useToast();
  const [creating, setCreating] = useState(false);
  const [confirming, setConfirming] = useState(null);
  const [resetting, setResetting] = useState(null);
  const [emailing, setEmailing] = useState(null);
  const [deleting, setDeleting] = useState(null);
  // Accounts can be deleted only in the online demo; a school deactivates them.
  const canDelete = Boolean(useOutletContext()?.school?.demo_full_access);
  const [busyId, setBusyId] = useState(null);
  const { data, loading, error, reload } = useLoad(
    (options) => api.getTeachers(options),
    'teachers',
    'Could not load the teacher accounts. Please try again.',
  );

  const setActive = async (teacher, active) => {
    setBusyId(teacher.id);
    try {
      await (active ? api.activateTeacher(teacher.id) : api.deactivateTeacher(teacher.id));
      toast.success(`${teacher.full_name || teacher.username} is now ${active ? 'active' : 'deactivated'}.`);
      setConfirming(null);
      reload();
    } catch (requestError) {
      toast.error(apiErrorMessage(requestError, 'Could not update the account. Please try again.'));
    } finally {
      setBusyId(null);
    }
  };

  const columns = [
    {
      header: 'Name',
      mobile: 'title',
      render: (teacher) => (
        <div>
          <p className="font-semibold text-slate-900">{teacher.full_name || teacher.username}</p>
          <p className="text-xs text-slate-600">{teacher.username}</p>
        </div>
      ),
    },
    { header: 'Email', render: (teacher) => teacher.email || 'Not recorded' },
    {
      header: 'Status',
      render: (teacher) => (
        <div className="flex flex-wrap items-center justify-end gap-1.5 md:justify-start">
          <Badge tone={teacher.is_active ? 'good' : 'bad'}>{teacher.is_active ? 'Active' : 'Deactivated'}</Badge>
          {teacher.must_change_password && <Badge tone="warn">Must change password</Badge>}
        </div>
      ),
    },
    {
      header: 'Action',
      mobile: 'actions',
      align: 'right',
      render: (teacher) => (
        <div className="flex flex-wrap items-center gap-2 md:justify-end">
          <Button variant="secondary" onClick={() => setEmailing(teacher)}>
            Change email<span className="sr-only"> for {teacher.full_name || teacher.username}</span>
          </Button>
          <Button variant="secondary" onClick={() => setResetting(teacher)}>
            Reset password<span className="sr-only"> for {teacher.full_name || teacher.username}</span>
          </Button>
          {teacher.is_active ? (
            <Button variant="secondary" disabled={busyId === teacher.id} onClick={() => setConfirming(teacher)}>
              Deactivate<span className="sr-only"> {teacher.full_name || teacher.username}</span>
            </Button>
          ) : (
            <Button variant="secondary" disabled={busyId === teacher.id} onClick={() => setActive(teacher, true)}>
              Activate<span className="sr-only"> {teacher.full_name || teacher.username}</span>
            </Button>
          )}
          {canDelete && (
            <Button variant="danger" onClick={() => setDeleting(teacher)}>
              Delete<span className="sr-only"> {teacher.full_name || teacher.username}</span>
            </Button>
          )}
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Teachers"
        subtitle="Create teacher sign-ins and switch them on or off."
        actions={(
          <Button onClick={() => setCreating(true)}>
            <UserPlus className="h-4 w-4" aria-hidden="true" />
            <span>Add Teacher</span>
          </Button>
        )}
      />
      <Card>
        <DataTable
          columns={columns}
          rows={data ?? []}
          loading={loading}
          error={error}
          onRetry={reload}
          loadingLabel="Loading teachers…"
          emptyState={{ title: 'No teacher accounts yet', message: 'Use Add Teacher to create the first one.' }}
        />
      </Card>

      {creating && (
        <CreateTeacherDialog
          onClose={() => setCreating(false)}
          onCreated={(name) => {
            setCreating(false);
            toast.success(`Account created for ${name}.`);
            reload();
          }}
        />
      )}
      {resetting && (
        <ResetPasswordDialog
          name={resetting.full_name || resetting.username}
          kept="Their classes and records are not changed."
          reset={(password) => api.resetTeacherPassword(resetting.id, password)}
          onClose={() => setResetting(null)}
          onDone={(name) => {
            setResetting(null);
            toast.success(`Password reset for ${name}. They must choose a new password when they next sign in.`);
            reload();
          }}
        />
      )}
      {emailing && (
        <ChangeEmailDialog
          name={emailing.full_name || emailing.username}
          current={emailing.email}
          save={(email, adminPassword) => api.updateTeacherEmail(emailing.id, email, adminPassword)}
          onClose={() => setEmailing(null)}
          onDone={(name, hasEmail) => {
            setEmailing(null);
            toast.success(hasEmail ? `Email address saved for ${name}.` : `Email address removed for ${name}.`);
            reload();
          }}
        />
      )}
      {deleting && (
        <DeleteAccountDialog
          name={deleting.full_name || deleting.username}
          remove={() => api.deleteTeacher(deleting.id)}
          onClose={() => setDeleting(null)}
          onDone={(name) => {
            setDeleting(null);
            toast.success(`${name}'s account was deleted.`);
            reload();
          }}
        />
      )}
      {confirming && (
        <ConfirmDeactivate
          teacher={confirming}
          busy={busyId === confirming.id}
          onCancel={() => setConfirming(null)}
          onConfirm={() => setActive(confirming, false)}
        />
      )}
    </div>
  );
}
