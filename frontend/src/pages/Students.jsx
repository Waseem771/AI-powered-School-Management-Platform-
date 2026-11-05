import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Archive, ArchiveRestore, Edit2, GraduationCap, Trash2, UserPlus, Users } from 'lucide-react';
import { api } from '../api/client';
import DataTable from '../components/DataTable';
import PdfButton from '../components/PdfButton';
import StudentFormDialog, { GRADES, SECTIONS } from '../components/StudentFormDialog';
import Button, { IconButton } from '../components/ui/Button';
import { SearchInput } from '../components/ui/Field';
import Modal from '../components/ui/Modal';
import { Badge, Card, FilterChips, PageHeader } from '../components/ui/Page';
import { ErrorNotice } from '../components/ui/States';
import { useToast } from '../components/ui/Toast';
import { apiErrorMessage } from '../lib/errors';
import { countLabel } from '../lib/uiState';

const ALL_GRADES = 'all';
const GRADE_FILTERS = [{ value: ALL_GRADES, label: 'All Grades' }, ...GRADES.map((grade) => ({ value: grade, label: grade }))];
const SECTION_FILTERS = [{ value: ALL_GRADES, label: 'All Sections' }, ...SECTIONS.map((section) => ({ value: section, label: `Section ${section}` }))];
const VIEWS = [
  { value: 'active', label: 'Current Students' },
  { value: 'archived', label: 'Archived' },
];

const CONFIRMATIONS = {
  archive: {
    title: (name) => `Archive ${name}?`,
    message: 'For a student who has left. They leave the current lists and counts. Their fee records, payments, and exam marks are kept, and you can restore them at any time.',
    button: 'Archive Student',
    variant: 'primary',
    done: (name) => `${name} was archived.`,
    call: api.archiveStudent,
  },
  restore: {
    title: (name) => `Restore ${name}?`,
    message: 'They return to the current lists and counts, with all their records.',
    button: 'Restore Student',
    variant: 'primary',
    done: (name) => `${name} was restored.`,
    call: api.restoreStudent,
  },
  delete: {
    title: (name) => `Permanently delete ${name}?`,
    message: 'Only for a record entered by mistake. This cannot be undone, and it is refused if the student has any fee or exam records.',
    button: 'Delete Permanently',
    variant: 'danger',
    done: (name) => `${name} was deleted.`,
    call: api.deleteStudent,
  },
};

function ConfirmActionDialog({ action, onClose, onDone }) {
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const details = CONFIRMATIONS[action.type];
  const { name, id } = action.student;

  const handleConfirm = async () => {
    setBusy(true);
    setError('');
    try {
      await details.call(id);
      onDone(details.done(name));
    } catch (err) {
      setError(apiErrorMessage(err, 'That did not work. Please try again.'));
      setBusy(false);
    }
  };

  return (
    <Modal
      title={details.title(name)}
      busy={busy}
      onClose={onClose}
      footer={(
        <>
          <Button variant="ghost" onClick={onClose} disabled={busy}>Cancel</Button>
          <Button variant={details.variant} onClick={handleConfirm} disabled={busy}>{busy ? 'Working…' : details.button}</Button>
        </>
      )}
    >
      <p className="text-sm leading-relaxed text-slate-700">{details.message}</p>
      <ErrorNotice>{error}</ErrorNotice>
    </Modal>
  );
}

export default function Students() {
  const [students, setStudents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [search, setSearch] = useState('');
  const [selectedGrade, setSelectedGrade] = useState(ALL_GRADES);
  const [selectedSection, setSelectedSection] = useState(ALL_GRADES);
  const [view, setView] = useState('active');
  // Null, or { student } for the form (student is null when adding).
  const [editing, setEditing] = useState(null);
  // Null, or { type: 'archive' | 'restore' | 'delete', student }.
  const [pendingAction, setPendingAction] = useState(null);
  const toast = useToast();

  const fetchStudents = async () => {
    try {
      setLoading(true);
      setLoadError('');
      const params = { status: view };
      if (selectedGrade !== ALL_GRADES) params.grade = selectedGrade;
      if (selectedSection !== ALL_GRADES) params.section = selectedSection;
      const res = await api.getStudents(params);
      setStudents(res.data);
    } catch (err) {
      setStudents([]);
      setLoadError(apiErrorMessage(err, 'Could not load students. Please try again.'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchStudents(); }, [selectedGrade, selectedSection, view]);

  const finish = (message) => {
    setEditing(null);
    setPendingAction(null);
    toast.success(message);
    fetchStudents();
  };

  const query = search.trim().toLowerCase();
  const shown = students.filter((student) => (
    !query
    || student.name.toLowerCase().includes(query)
    || student.roll_number.toLowerCase().includes(query)
    || student.guardian_name.toLowerCase().includes(query)
    || student.phone.includes(query)
  ));

  const columns = [
    { header: 'Name', mobile: 'title', render: (student) => (
      <div>
        <Link to={`/students/${student.id}`} className="font-bold text-slate-900 underline-offset-2 hover:underline">{student.name}</Link>
        <span className="ml-2 font-mono text-xs font-semibold text-brand-700 md:hidden">#{student.roll_number}</span>
        <div className="text-xs text-slate-600">Born: {student.dob || 'Not recorded'}</div>
      </div>
    ) },
    { header: 'Roll No', render: (student) => <span className="font-mono font-semibold text-brand-700">#{student.roll_number}</span> },
    { header: 'Class', render: (student) => <Badge>{student.grade} - {student.section}</Badge> },
    { header: 'Guardian', render: (student) => student.guardian_name },
    { header: 'Phone', render: (student) => <span className="font-mono text-xs">{student.phone}</span> },
    { header: 'Actions', align: 'right', mobile: 'actions', render: (student) => (
      <div className="flex flex-wrap items-center gap-1 md:justify-end">
        <PdfButton fetchPdf={() => api.getReportCardPdf(student.id)} title={`Report card for ${student.name}`}>
          <GraduationCap className="h-4 w-4" aria-hidden="true" />
          <span>Report Card</span>
        </PdfButton>
        <IconButton label={`Edit ${student.name}`} onClick={() => setEditing({ student })}><Edit2 className="h-4 w-4" /></IconButton>
        {view === 'active' ? (
          <IconButton label={`Archive ${student.name}`} onClick={() => setPendingAction({ type: 'archive', student })}><Archive className="h-4 w-4" /></IconButton>
        ) : (
          <>
            <IconButton label={`Restore ${student.name}`} onClick={() => setPendingAction({ type: 'restore', student })}><ArchiveRestore className="h-4 w-4" /></IconButton>
            <IconButton label={`Delete ${student.name} permanently`} onClick={() => setPendingAction({ type: 'delete', student })}><Trash2 className="h-4 w-4" /></IconButton>
          </>
        )}
      </div>
    ) },
  ];

  const isFiltered = Boolean(query) || selectedGrade !== ALL_GRADES || selectedSection !== ALL_GRADES;
  const emptyState = isFiltered
    ? { icon: Users, title: 'No students match', message: 'Try a different search, grade, or section.' }
    : view === 'archived'
      ? { icon: Archive, title: 'No archived students', message: 'Students who leave the school appear here, with all their records.' }
      : {
          icon: Users,
          title: 'No students yet',
          message: 'Add your first student to start issuing fees and entering marks.',
          action: <Button onClick={() => setEditing({ student: null })}><UserPlus className="h-4 w-4" aria-hidden="true" /><span>Add Student</span></Button>,
        };

  return (
    <div className="space-y-5">
      <PageHeader
        title="Students"
        subtitle="Enrollment records, classes, and guardian contacts."
        actions={<Button onClick={() => setEditing({ student: null })}><UserPlus className="h-4 w-4" aria-hidden="true" /><span>Add Student</span></Button>}
      />

      <FilterChips label="Which students to show" options={VIEWS} value={view} onChange={setView} />

      <Card className="space-y-3 p-4">
        <SearchInput label="Search by name, roll number, or phone" value={search} onChange={(event) => setSearch(event.target.value)} className="w-full md:max-w-md" />
        <FilterChips label="Grade" options={GRADE_FILTERS} value={selectedGrade} onChange={setSelectedGrade} />
        <FilterChips label="Section" options={SECTION_FILTERS} value={selectedSection} onChange={setSelectedSection} />
      </Card>

      <Card className="overflow-hidden">
        <DataTable
          columns={columns}
          rows={shown}
          loading={loading}
          error={loadError}
          onRetry={fetchStudents}
          loadingLabel="Loading students…"
          emptyState={emptyState}
        />
        {!loading && !loadError && shown.length > 0 && (
          <p className="border-t border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
            Showing {countLabel(shown.length, view === 'archived' ? 'archived student' : 'current student')}
          </p>
        )}
      </Card>

      {editing && <StudentFormDialog student={editing.student} onClose={() => setEditing(null)} onSaved={finish} />}
      {pendingAction && <ConfirmActionDialog action={pendingAction} onClose={() => setPendingAction(null)} onDone={finish} />}
    </div>
  );
}
