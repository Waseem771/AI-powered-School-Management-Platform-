import React, { useState } from 'react';
import { Pencil, Plus, Trash2 } from 'lucide-react';
import { api } from '../api/client';
import DataTable from '../components/DataTable';
import Button from '../components/ui/Button';
import { SelectField } from '../components/ui/Field';
import Modal from '../components/ui/Modal';
import { Card, PageHeader } from '../components/ui/Page';
import { ErrorNotice, ErrorState, LoadingState } from '../components/ui/States';
import { useToast } from '../components/ui/Toast';
import { classLabel } from '../lib/attendance';
import { apiErrorMessage } from '../lib/errors';
import { useLoad } from '../lib/useLoad';

const FORM_ID = 'assignment-form';

function AssignmentDialog({ options, assignment, onClose, onSaved }) {
  const activeTeachers = options.teachers.filter((teacher) => teacher.is_active || teacher.id === assignment?.teacher_id);
  const currentYear = options.academic_years.find((year) => year.is_current) ?? options.academic_years[0];
  const [form, setForm] = useState({
    teacher_id: String(assignment?.teacher_id ?? activeTeachers[0]?.id ?? ''),
    grade: assignment?.grade ?? options.grades[0],
    section: assignment?.section ?? options.sections[0],
    academic_year_id: String(assignment?.academic_year_id ?? currentYear?.id ?? ''),
  });
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const set = (field) => (event) => setForm((current) => ({ ...current, [field]: event.target.value }));

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!form.teacher_id) {
      setError('Choose a teacher. Create teacher accounts under Teachers first.');
      return;
    }
    setError('');
    setSaving(true);
    const body = { ...form, teacher_id: Number(form.teacher_id), academic_year_id: Number(form.academic_year_id) };
    try {
      if (assignment) await api.updateAssignment(assignment.id, body);
      else await api.createAssignment(body);
      onSaved();
    } catch (requestError) {
      setError(apiErrorMessage(requestError, 'Could not save the assignment. Please try again.'));
      setSaving(false);
    }
  };

  return (
    <Modal
      title={assignment ? 'Edit Assignment' : 'Assign Teacher to Class'}
      description="A teacher can have several classes, and a class can have several teachers."
      busy={saving}
      onClose={onClose}
      footer={(
        <>
          <Button variant="ghost" onClick={onClose} disabled={saving}>Cancel</Button>
          <Button type="submit" form={FORM_ID} disabled={saving}>{saving ? 'Saving…' : 'Save'}</Button>
        </>
      )}
    >
      <ErrorNotice>{error}</ErrorNotice>
      <form id={FORM_ID} onSubmit={handleSubmit} className="space-y-4">
        <SelectField
          label="Teacher"
          value={form.teacher_id}
          onChange={set('teacher_id')}
          options={activeTeachers.length ? activeTeachers.map((t) => ({ value: String(t.id), label: `${t.name} (${t.username})` })) : [{ value: '', label: 'No active teachers' }]}
        />
        <div className="grid grid-cols-2 gap-4">
          <SelectField label="Grade" value={form.grade} onChange={set('grade')} options={options.grades.map((grade) => ({ value: grade, label: grade }))} />
          <SelectField label="Section" value={form.section} onChange={set('section')} options={options.sections.map((section) => ({ value: section, label: section }))} />
        </div>
        <SelectField
          label="Academic session"
          value={form.academic_year_id}
          onChange={set('academic_year_id')}
          options={options.academic_years.map((year) => ({ value: String(year.id), label: `${year.label}${year.is_current ? ' (current)' : ''}` }))}
        />
      </form>
    </Modal>
  );
}

function ConfirmRemove({ assignment, busy, onCancel, onConfirm }) {
  return (
    <Modal
      title="Remove assignment?"
      size="sm"
      busy={busy}
      onClose={onCancel}
      footer={(
        <>
          <Button variant="ghost" onClick={onCancel} disabled={busy}>Cancel</Button>
          <Button variant="danger" onClick={onConfirm} disabled={busy}>{busy ? 'Removing…' : 'Remove'}</Button>
        </>
      )}
    >
      <p className="text-sm text-slate-700">
        {assignment.teacher_name} will no longer see {classLabel(assignment.grade, assignment.section)} or its students.
        Attendance they already recorded is kept.
      </p>
    </Modal>
  );
}

export default function TeacherAssignments() {
  const toast = useToast();
  const [teacherFilter, setTeacherFilter] = useState('');
  const [yearFilter, setYearFilter] = useState('');
  const [editing, setEditing] = useState(null); // { assignment } or { assignment: null } to add
  const [removing, setRemoving] = useState(null);
  const [busy, setBusy] = useState(false);

  const optionsLoad = useLoad((request) => api.getAssignmentOptions(request), 'assignment-options', 'Could not load teachers and classes.');
  const listLoad = useLoad(
    (request) => api.getAssignments({ teacher_id: teacherFilter || undefined, academic_year_id: yearFilter || undefined }, request),
    `assignments-${teacherFilter}-${yearFilter}`,
    'Could not load the assignments. Please try again.',
  );

  const refresh = () => listLoad.reload();

  const handleRemove = async () => {
    setBusy(true);
    try {
      await api.deleteAssignment(removing.id);
      toast.success('Assignment removed.');
      setRemoving(null);
      refresh();
    } catch (requestError) {
      toast.error(apiErrorMessage(requestError, 'Could not remove the assignment. Please try again.'));
    } finally {
      setBusy(false);
    }
  };

  if (optionsLoad.loading) return <LoadingState label="Loading…" />;
  if (optionsLoad.error) return <ErrorState message={optionsLoad.error} onRetry={optionsLoad.reload} />;
  const options = optionsLoad.data;

  const columns = [
    {
      header: 'Teacher',
      mobile: 'title',
      render: (row) => (
        <div>
          <p className="font-semibold text-slate-900">{row.teacher_name}</p>
          <p className="text-xs text-slate-600">{row.teacher_username}{row.teacher_active ? '' : ' · deactivated'}</p>
        </div>
      ),
    },
    { header: 'Class', render: (row) => classLabel(row.grade, row.section) },
    { header: 'Session', render: (row) => row.academic_year },
    { header: 'Students', align: 'right', render: (row) => row.enrolled },
    {
      header: 'Actions',
      mobile: 'actions',
      align: 'right',
      render: (row) => (
        <div className="flex flex-wrap justify-end gap-2">
          <Button variant="secondary" onClick={() => setEditing({ assignment: row })}>
            <Pencil className="h-4 w-4" aria-hidden="true" />
            <span>Edit<span className="sr-only"> {row.teacher_name}, {classLabel(row.grade, row.section)}</span></span>
          </Button>
          <Button variant="secondary" onClick={() => setRemoving(row)}>
            <Trash2 className="h-4 w-4" aria-hidden="true" />
            <span>Remove<span className="sr-only"> {row.teacher_name}, {classLabel(row.grade, row.section)}</span></span>
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Teacher Assignments"
        subtitle="Choose which classes each teacher can see and take attendance for."
        actions={<Button onClick={() => setEditing({ assignment: null })}><Plus className="h-4 w-4" aria-hidden="true" /><span>Assign Teacher</span></Button>}
      />
      <Card>
        <div className="grid gap-4 border-b border-slate-200 p-4 sm:grid-cols-2">
          <SelectField
            label="Teacher"
            value={teacherFilter}
            onChange={(event) => setTeacherFilter(event.target.value)}
            options={[{ value: '', label: 'All teachers' }, ...options.teachers.map((t) => ({ value: String(t.id), label: t.name }))]}
          />
          <SelectField
            label="Academic session"
            value={yearFilter}
            onChange={(event) => setYearFilter(event.target.value)}
            options={[{ value: '', label: 'All sessions' }, ...options.academic_years.map((y) => ({ value: String(y.id), label: y.label }))]}
          />
        </div>
        <DataTable
          columns={columns}
          rows={listLoad.data ?? []}
          loading={listLoad.loading}
          error={listLoad.error}
          onRetry={listLoad.reload}
          loadingLabel="Loading assignments…"
          emptyState={{ title: 'No assignments yet', message: options.teachers.length ? 'Use Assign Teacher to give a teacher a class.' : 'Create a teacher account under Teachers first.' }}
        />
      </Card>

      {editing && (
        <AssignmentDialog
          options={options}
          assignment={editing.assignment}
          onClose={() => setEditing(null)}
          onSaved={() => {
            toast.success(editing.assignment ? 'Assignment updated.' : 'Teacher assigned.');
            setEditing(null);
            refresh();
          }}
        />
      )}
      {removing && <ConfirmRemove assignment={removing} busy={busy} onCancel={() => setRemoving(null)} onConfirm={handleRemove} />}
    </div>
  );
}
