import React, { useState } from 'react';
import { UserPlus, X } from 'lucide-react';
import { api } from '../api/client';
import DataTable from '../components/DataTable';
import ChangeEmailDialog from '../components/ChangeEmailDialog';
import ResetPasswordDialog from '../components/ResetPasswordDialog';
import StudentPicker from '../components/StudentPicker';
import Button, { IconButton } from '../components/ui/Button';
import { SelectField, TextField } from '../components/ui/Field';
import Modal from '../components/ui/Modal';
import { Badge, Card, PageHeader } from '../components/ui/Page';
import { ErrorNotice } from '../components/ui/States';
import { useToast } from '../components/ui/Toast';
import { apiErrorMessage } from '../lib/errors';
import { examLabel } from '../lib/exams';
import { RELATIONSHIP_OPTIONS, classText } from '../lib/parent';
import { studentLabel } from '../lib/uiState';
import { useLoad } from '../lib/useLoad';

const MIN_PASSWORD_LENGTH = 10;
const FORM_ID = 'create-parent-form';
const EMPTY_FORM = { full_name: '', username: '', email: '', password: '', relationship: '' };

function CreateParentDialog({ onClose, onCreated }) {
  const [form, setForm] = useState(EMPTY_FORM);
  const [children, setChildren] = useState([]);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const set = (field) => (event) => setForm((current) => ({ ...current, [field]: event.target.value }));

  const addChild = (student) => {
    if (student && !children.some((child) => child.id === student.id)) setChildren((current) => [...current, student]);
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    if (!form.full_name.trim() || !form.username.trim()) {
      setError('Enter the parent\'s full name and a username.');
      return;
    }
    if (form.password.length < MIN_PASSWORD_LENGTH) {
      setError(`The password must be at least ${MIN_PASSWORD_LENGTH} characters.`);
      return;
    }
    if (children.length === 0) {
      setError('Add at least one child for this parent.');
      return;
    }
    setSaving(true);
    try {
      await api.createParent({
        full_name: form.full_name.trim(),
        username: form.username.trim(),
        email: form.email.trim() || null,
        password: form.password,
        relationship: form.relationship || null,
        student_ids: children.map((child) => child.id),
      });
      onCreated(form.full_name.trim());
    } catch (requestError) {
      setError(apiErrorMessage(requestError, 'Could not create the account. Please try again.'));
      setSaving(false);
    }
  };

  return (
    <Modal
      title="Add Parent"
      description="Creates a sign-in for a parent and links their children. Share the password with them privately."
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
        <TextField label="Initial password" type="password" hint={`At least ${MIN_PASSWORD_LENGTH} characters. The parent can change it after signing in.`} value={form.password} onChange={set('password')} autoComplete="new-password" />
        <SelectField label="Relationship to the children" options={RELATIONSHIP_OPTIONS} value={form.relationship} onChange={set('relationship')} />
        <div className="space-y-2">
          <StudentPicker label="Add a child" student={null} onChange={addChild} />
          {children.length > 0 && (
            <ul aria-label="Children to link" className="space-y-1">
              {children.map((child) => (
                <li key={child.id} className="flex items-center justify-between gap-2 rounded-xl bg-slate-50 pl-3 text-sm text-slate-800">
                  <span>{studentLabel(child)}</span>
                  <IconButton label={`Remove ${child.name}`} onClick={() => setChildren((current) => current.filter((item) => item.id !== child.id))}>
                    <X className="h-4 w-4" aria-hidden="true" />
                  </IconButton>
                </li>
              ))}
            </ul>
          )}
        </div>
      </form>
    </Modal>
  );
}

function ManageChildrenDialog({ parent, onClose, onChanged }) {
  const toast = useToast();
  const [picked, setPicked] = useState(null);
  const [relationship, setRelationship] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const run = async (action, success) => {
    setBusy(true);
    setError('');
    try {
      await action();
      toast.success(success);
      setPicked(null);
      onChanged();
    } catch (requestError) {
      setError(apiErrorMessage(requestError, 'Could not save the change. Please try again.'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal
      title={`Children of ${parent.full_name || parent.username}`}
      description="A parent sees only the children listed here."
      busy={busy}
      onClose={onClose}
      footer={<Button variant="secondary" onClick={onClose} disabled={busy}>Done</Button>}
    >
      <ErrorNotice>{error}</ErrorNotice>
      {parent.children.length === 0 ? (
        <p className="text-sm text-slate-600">No children are linked, so this parent sees nothing.</p>
      ) : (
        <ul aria-label="Linked children" className="space-y-1">
          {parent.children.map((child) => (
            <li key={child.student_id} className="flex items-center justify-between gap-2 rounded-xl bg-slate-50 pl-3 text-sm text-slate-800">
              <span>
                {child.name} <span className="text-xs text-slate-600">(#{child.roll_number}, {classText(child)}{child.relationship ? `, ${child.relationship}` : ''})</span>
              </span>
              <IconButton
                label={`Remove ${child.name}`}
                disabled={busy}
                onClick={() => run(() => api.unlinkParentChild(parent.id, child.student_id), `${child.name} is no longer linked.`)}
              >
                <X className="h-4 w-4" aria-hidden="true" />
              </IconButton>
            </li>
          ))}
        </ul>
      )}
      <div className="mt-5 space-y-3 border-t border-slate-200 pt-4">
        {/* The relationship comes first, so the dialog does not open with the student list already showing. */}
        <SelectField label="Relationship" options={RELATIONSHIP_OPTIONS} value={relationship} onChange={(event) => setRelationship(event.target.value)} />
        <StudentPicker label="Link another child" student={picked} onChange={setPicked} />
        <Button
          disabled={!picked || busy}
          onClick={() => run(
            () => api.linkParentChild(parent.id, { student_id: picked.id, relationship: relationship || null }),
            `${picked.name} is now linked.`,
          )}
        >
          Link child
        </Button>
      </div>
    </Modal>
  );
}

function ConfirmDeactivate({ parent, busy, onCancel, onConfirm }) {
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
        {parent.full_name || parent.username} will be signed out at once and will not be able to sign in
        until you activate the account again. Nothing is deleted.
      </p>
    </Modal>
  );
}

function ConfirmPublish({ exam, busy, onCancel, onConfirm }) {
  return (
    <Modal
      title="Show these results to parents?"
      size="sm"
      busy={busy}
      onClose={onCancel}
      footer={(
        <>
          <Button variant="ghost" onClick={onCancel} disabled={busy}>Cancel</Button>
          <Button onClick={onConfirm} disabled={busy}>{busy ? 'Saving…' : 'Show to parents'}</Button>
        </>
      )}
    >
      <p className="text-sm text-slate-700">
        Parents will see their own child's marks, grades and report card for <b>{examLabel(exam)}</b>.
        Check that every mark is entered first. You can hide the exam again at any time.
      </p>
    </Modal>
  );
}

function ResultVisibility() {
  const toast = useToast();
  const [confirming, setConfirming] = useState(null);
  const [busyKey, setBusyKey] = useState(null);
  const { data, loading, error, reload } = useLoad(
    (options) => api.getResultPublishing(options),
    'result-publishing',
    'Could not load the exams. Please try again.',
  );

  const setPublished = async (exam, published) => {
    setBusyKey(`${exam.academic_year_id}|${exam.exam_type}`);
    try {
      await api.setResultPublished({ academic_year_id: exam.academic_year_id, exam_type: exam.exam_type, published });
      toast.success(`${examLabel(exam)} is now ${published ? 'visible to parents' : 'hidden from parents'}.`);
      setConfirming(null);
      reload();
    } catch (requestError) {
      toast.error(apiErrorMessage(requestError, 'Could not update the exam. Please try again.'));
    } finally {
      setBusyKey(null);
    }
  };

  const columns = [
    { header: 'Exam', mobile: 'title', render: (exam) => <span className="font-semibold text-slate-900">{examLabel(exam)}</span> },
    { header: 'Students with marks', render: (exam) => exam.students_with_marks },
    {
      header: 'Parents can see it',
      render: (exam) => <Badge tone={exam.published ? 'good' : 'neutral'}>{exam.published ? 'Visible' : 'Hidden'}</Badge>,
    },
    {
      header: 'Action',
      mobile: 'actions',
      align: 'right',
      render: (exam) => (exam.published ? (
        <Button variant="secondary" disabled={busyKey !== null} onClick={() => setPublished(exam, false)}>
          Hide<span className="sr-only"> {examLabel(exam)}</span>
        </Button>
      ) : (
        <Button variant="secondary" disabled={busyKey !== null} onClick={() => setConfirming(exam)}>
          Show to parents<span className="sr-only"> {examLabel(exam)}</span>
        </Button>
      )),
    },
  ];

  return (
    <section aria-labelledby="visibility-heading" className="space-y-2">
      <div>
        <h2 id="visibility-heading" className="text-base font-bold text-slate-900">Results shown to parents</h2>
        <p className="text-sm text-slate-600">Parents see an exam only after you show it here. Marks of other exams stay hidden.</p>
      </div>
      <Card>
        <DataTable
          columns={columns}
          rows={data ?? []}
          rowKey={(exam) => `${exam.academic_year_id}|${exam.exam_type}`}
          loading={loading}
          error={error}
          onRetry={reload}
          loadingLabel="Loading exams…"
          emptyState={{ title: 'No exam marks yet', message: 'Exams appear here once marks are entered.' }}
        />
      </Card>
      {confirming && (
        <ConfirmPublish
          exam={confirming}
          busy={busyKey !== null}
          onCancel={() => setConfirming(null)}
          onConfirm={() => setPublished(confirming, true)}
        />
      )}
    </section>
  );
}

export default function Parents() {
  const toast = useToast();
  const [creating, setCreating] = useState(false);
  const [confirming, setConfirming] = useState(null);
  const [managingId, setManagingId] = useState(null);
  const [resetting, setResetting] = useState(null);
  const [emailing, setEmailing] = useState(null);
  const [busyId, setBusyId] = useState(null);
  const { data, loading, error, reload } = useLoad(
    (options) => api.getParents(options),
    'parents',
    'Could not load the parent accounts. Please try again.',
  );
  const managing = (data ?? []).find((parent) => parent.id === managingId) ?? null;

  const setActive = async (parent, active) => {
    setBusyId(parent.id);
    try {
      await (active ? api.activateParent(parent.id) : api.deactivateParent(parent.id));
      toast.success(`${parent.full_name || parent.username} is now ${active ? 'active' : 'deactivated'}.`);
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
      render: (parent) => (
        <div>
          <p className="font-semibold text-slate-900">{parent.full_name || parent.username}</p>
          <p className="text-xs text-slate-600">{parent.username}</p>
          <p className="text-xs text-slate-600">{parent.email || 'No email on file'}</p>
        </div>
      ),
    },
    {
      header: 'Children',
      render: (parent) => (parent.children.length === 0 ? 'None linked' : (
        <ul className="space-y-0.5">
          {parent.children.map((child) => (
            <li key={child.student_id} className="text-sm">{child.name} <span className="text-xs text-slate-600">({classText(child)})</span></li>
          ))}
        </ul>
      )),
    },
    {
      header: 'Status',
      render: (parent) => (
        <div className="flex flex-wrap items-center justify-end gap-1.5 md:justify-start">
          <Badge tone={parent.is_active ? 'good' : 'bad'}>{parent.is_active ? 'Active' : 'Deactivated'}</Badge>
          {parent.must_change_password && <Badge tone="warn">Must change password</Badge>}
        </div>
      ),
    },
    {
      header: 'Action',
      mobile: 'actions',
      align: 'right',
      render: (parent) => (
        <div className="flex flex-wrap items-center gap-2 md:justify-end">
          <Button variant="secondary" onClick={() => setManagingId(parent.id)}>
            Children<span className="sr-only"> of {parent.full_name || parent.username}</span>
          </Button>
          <Button variant="secondary" onClick={() => setEmailing(parent)}>
            Change email<span className="sr-only"> for {parent.full_name || parent.username}</span>
          </Button>
          <Button variant="secondary" onClick={() => setResetting(parent)}>
            Reset password<span className="sr-only"> for {parent.full_name || parent.username}</span>
          </Button>
          {parent.is_active ? (
            <Button variant="secondary" disabled={busyId === parent.id} onClick={() => setConfirming(parent)}>
              Deactivate<span className="sr-only"> {parent.full_name || parent.username}</span>
            </Button>
          ) : (
            <Button variant="secondary" disabled={busyId === parent.id} onClick={() => setActive(parent, true)}>
              Activate<span className="sr-only"> {parent.full_name || parent.username}</span>
            </Button>
          )}
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Parents"
        subtitle="Create parent sign-ins, link their children, and choose which results parents can see."
        actions={(
          <Button onClick={() => setCreating(true)}>
            <UserPlus className="h-4 w-4" aria-hidden="true" />
            <span>Add Parent</span>
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
          loadingLabel="Loading parents…"
          emptyState={{ title: 'No parent accounts yet', message: 'Use Add Parent to create the first one.' }}
        />
      </Card>

      <ResultVisibility />

      {creating && (
        <CreateParentDialog
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
          kept="Their children and records are not changed."
          reset={(password) => api.resetParentPassword(resetting.id, password)}
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
          save={(email, adminPassword) => api.updateParentEmail(emailing.id, email, adminPassword)}
          onClose={() => setEmailing(null)}
          onDone={(name, hasEmail) => {
            setEmailing(null);
            toast.success(hasEmail ? `Email address saved for ${name}.` : `Email address removed for ${name}.`);
            reload();
          }}
        />
      )}
      {managing && <ManageChildrenDialog parent={managing} onClose={() => setManagingId(null)} onChanged={reload} />}
      {confirming && (
        <ConfirmDeactivate
          parent={confirming}
          busy={busyId === confirming.id}
          onCancel={() => setConfirming(null)}
          onConfirm={() => setActive(confirming, false)}
        />
      )}
    </div>
  );
}
