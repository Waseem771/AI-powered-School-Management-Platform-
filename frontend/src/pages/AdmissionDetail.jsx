import React, { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, Banknote, ClipboardCheck, GraduationCap, Pencil, Plus, Sparkles } from 'lucide-react';
import { api } from '../api/client';
import Button, { buttonClass } from '../components/ui/Button';
import { Field, INPUT_CLASS, SelectField, TextField } from '../components/ui/Field';
import Modal from '../components/ui/Modal';
import { Badge, Card, PageHeader } from '../components/ui/Page';
import { EmptyState, ErrorNotice, ErrorState, LoadingState } from '../components/ui/States';
import { useToast } from '../components/ui/Toast';
import { STATUS_TONES, assessmentProblems, statusConfirmation, testPercentage } from '../lib/admissions';
import { formatDate } from '../lib/activity';
import { apiErrorMessage } from '../lib/errors';
import { useLoad } from '../lib/useLoad';

const AI_NOTE = 'Drafted automatically from this application, and it can be wrong. Please read and correct it before using it. It does not decide anything.';

function Row({ label, children }) {
  return (
    <div className="flex items-baseline justify-between gap-4 py-1.5 text-sm">
      <dt className="shrink-0 text-xs font-semibold text-slate-600">{label}</dt>
      <dd className="min-w-0 text-right text-slate-800">{children || <span className="text-slate-500">Not given</span>}</dd>
    </div>
  );
}

function StatusDialog({ application, target, onClose, onDone }) {
  const toast = useToast();
  const copy = statusConfirmation(target.value, target.label);
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const confirm = async () => {
    if (copy.needsNote && note.trim().length < 5) {
      setError('Please write the reason, at least a few words.');
      return;
    }
    setBusy(true);
    setError('');
    try {
      await api.changeApplicationStatus(application.id, { to_status: target.value, note: note.trim() || null });
      toast.success(`Application is now "${target.label}".`);
      onDone();
    } catch (err) {
      setError(apiErrorMessage(err, 'The status could not be changed.'));
      setBusy(false);
    }
  };

  return (
    <Modal
      title={copy.title}
      description={copy.body}
      busy={busy}
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={busy}>Cancel</Button>
          <Button variant={target.value === 'rejected' ? 'danger' : 'primary'} onClick={confirm} disabled={busy}>{busy ? 'Saving…' : copy.confirm}</Button>
        </>
      }
    >
      <ErrorNotice>{error}</ErrorNotice>
      <Field label={copy.needsNote ? 'Reason *' : 'Note (optional)'}>
        {(field) => <textarea rows={3} maxLength={1000} className={INPUT_CLASS} value={note} onChange={(event) => setNote(event.target.value)} {...field} />}
      </Field>
    </Modal>
  );
}

function AssessmentDialog({ application, onClose, onDone }) {
  const toast = useToast();
  const [form, setForm] = useState({ test_date: '', subject: '', max_marks: '', obtained_marks: '', remarks: '', interview_notes: '' });
  const [tried, setTried] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const problems = tried ? assessmentProblems(form) : {};
  const percent = testPercentage(form.obtained_marks, form.max_marks);
  const set = (name) => (event) => setForm((current) => ({ ...current, [name]: event.target.value }));

  const save = async (event) => {
    event.preventDefault();
    setTried(true);
    if (Object.keys(assessmentProblems(form)).length) return;
    setBusy(true);
    setError('');
    try {
      await api.addApplicationAssessment(application.id, {
        test_date: form.test_date,
        subject: form.subject.trim(),
        max_marks: Number(form.max_marks),
        obtained_marks: Number(form.obtained_marks),
        remarks: form.remarks.trim() || null,
        interview_notes: form.interview_notes.trim() || null,
      });
      toast.success('Entry test recorded.');
      onDone();
    } catch (err) {
      setError(apiErrorMessage(err, 'The entry test could not be saved.'));
      setBusy(false);
    }
  };

  return (
    <Modal
      title="Record entry test or interview"
      busy={busy}
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={busy}>Cancel</Button>
          <Button type="submit" form="assessment-form" disabled={busy}>{busy ? 'Saving…' : 'Save'}</Button>
        </>
      }
    >
      <form id="assessment-form" onSubmit={save} noValidate className="space-y-4">
        <ErrorNotice>{error}</ErrorNotice>
        <TextField label="Subject or assessment name *" value={form.subject} onChange={set('subject')} />
        {problems.subject && <p role="alert" className="text-xs font-semibold text-rose-700">{problems.subject}</p>}
        <Field label="Test date *">{(field) => <input type="date" className={INPUT_CLASS} value={form.test_date} onChange={set('test_date')} {...field} />}</Field>
        {problems.test_date && <p role="alert" className="text-xs font-semibold text-rose-700">{problems.test_date}</p>}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <TextField label="Maximum marks *" type="number" inputMode="decimal" min="1" value={form.max_marks} onChange={set('max_marks')} />
            {problems.max_marks && <p role="alert" className="mt-1 text-xs font-semibold text-rose-700">{problems.max_marks}</p>}
          </div>
          <div>
            <TextField label="Marks obtained *" type="number" inputMode="decimal" min="0" value={form.obtained_marks} onChange={set('obtained_marks')} />
            {problems.obtained_marks && <p role="alert" className="mt-1 text-xs font-semibold text-rose-700">{problems.obtained_marks}</p>}
          </div>
        </div>
        <p aria-live="polite" className="text-sm text-slate-700">Percentage: <strong>{percent === null ? '—' : `${percent}%`}</strong></p>
        <Field label="Staff remarks (optional)">{(field) => <textarea rows={2} maxLength={1000} className={INPUT_CLASS} value={form.remarks} onChange={set('remarks')} {...field} />}</Field>
        <Field label="Interview notes (optional)">{(field) => <textarea rows={2} maxLength={1000} className={INPUT_CLASS} value={form.interview_notes} onChange={set('interview_notes')} {...field} />}</Field>
      </form>
    </Modal>
  );
}

function EnrollDialog({ application, onClose, onDone }) {
  const toast = useToast();
  const meta = useLoad((options) => api.getAdmissionOptions(options), 'options', 'Options could not be loaded.');
  const roll = useLoad((options) => api.getNextRollNumber(options), 'roll', 'The next roll number could not be found.');
  const [section, setSection] = useState('A');
  const [rollNumber, setRollNumber] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const shownRoll = rollNumber ?? roll.data?.roll_number ?? '';

  const enroll = async () => {
    setBusy(true);
    setError('');
    try {
      const response = await api.enrollApplicant(application.id, {
        section,
        confirm_academic_year_id: application.academic_year_id,
        confirm_grade: application.applying_grade,
        roll_number: shownRoll.trim() || null,
      });
      toast.success(`${application.student_name} is enrolled with roll number ${response.data.roll_number}.`);
      onDone();
    } catch (err) {
      setError(apiErrorMessage(err, 'The applicant could not be enrolled.'));
      setBusy(false);
    }
  };

  return (
    <Modal
      title="Enrol this applicant"
      description="This adds them to Students. Please check the details below."
      busy={busy}
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={busy}>Cancel</Button>
          <Button variant="success" onClick={enroll} disabled={busy || meta.loading || roll.loading || !shownRoll.trim()}>{busy ? 'Enrolling…' : 'Enrol student'}</Button>
        </>
      }
    >
      <ErrorNotice>{error || meta.error || roll.error}</ErrorNotice>
      <dl className="divide-y divide-slate-100 rounded-xl border border-slate-200 px-3">
        <Row label="Student">{application.student_name}</Row>
        <Row label="Academic session">{application.academic_session}</Row>
        <Row label="Class">{application.applying_grade}</Row>
      </dl>
      <SelectField label="Section" value={section} onChange={(event) => setSection(event.target.value)} options={(meta.data?.sections || ['A', 'B']).map((value) => ({ value, label: value }))} />
      <TextField label="Roll number" hint="The next free number is filled in. Change it only if the school uses another." value={shownRoll} onChange={(event) => setRollNumber(event.target.value)} />
    </Modal>
  );
}

function InvoiceDialog({ application, onClose }) {
  const toast = useToast();
  const policy = useLoad((options) => api.getApplicationFeePolicy(application.id, options), 'policy', 'The fee setting could not be loaded.');
  const now = new Date();
  const [amount, setAmount] = useState('');
  const [month, setMonth] = useState(now.toLocaleString('en-US', { month: 'long', year: 'numeric' }));
  const [due, setDue] = useState(new Date(now.getTime() + 10 * 86400000).toISOString().slice(0, 10));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const shownAmount = amount || (policy.data?.configured ? String(policy.data.monthly_fee) : '');

  const create = async () => {
    setBusy(true);
    setError('');
    try {
      await api.generateChallan({ student_id: application.student_id, amount: Number(shownAmount), month: month.trim(), due_date: due });
      toast.success('Invoice created. Open the student to print the challan.');
      onClose();
    } catch (err) {
      setError(apiErrorMessage(err, 'The invoice could not be created.'));
      setBusy(false);
    }
  };

  return (
    <Modal
      title="Create an invoice"
      description="Uses the normal Fees rules. Nothing is charged until you confirm here."
      busy={busy}
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={busy}>Cancel</Button>
          <Button onClick={create} disabled={busy || policy.loading || !(Number(shownAmount) > 0)}>{busy ? 'Creating…' : 'Create invoice'}</Button>
        </>
      }
    >
      <ErrorNotice>{error || policy.error}</ErrorNotice>
      {policy.data && !policy.data.configured && (
        <p className="rounded-xl bg-amber-50 p-3 text-sm text-amber-900">No monthly fee is set up for this class, so no amount is suggested. Enter the amount the school has agreed.</p>
      )}
      <TextField label="Amount (Rs.)" type="number" inputMode="decimal" min="1" value={shownAmount} onChange={(event) => setAmount(event.target.value)} />
      <TextField label="Month" hint="For example December 2026" value={month} onChange={(event) => setMonth(event.target.value)} />
      <Field label="Due date">{(field) => <input type="date" className={INPUT_CLASS} value={due} onChange={(event) => setDue(event.target.value)} {...field} />}</Field>
    </Modal>
  );
}

function AssistantCard({ application }) {
  const [result, setResult] = useState(null);
  const [draft, setDraft] = useState('');
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [question, setQuestion] = useState('');
  const [policy, setPolicy] = useState(null);
  const missing = application.documents.filter((item) => !item.received).map((item) => item.name);

  const run = async (name, call, pick) => {
    setBusy(name);
    setError('');
    try {
      const response = await call();
      const text = pick(response.data);
      setResult({ kind: name, notice: response.data.message });
      setDraft(text || '');
    } catch (err) {
      setError(apiErrorMessage(err, 'The assistant is not available right now. You can carry on without it.'));
    } finally {
      setBusy('');
    }
  };

  const ask = async (event) => {
    event.preventDefault();
    if (question.trim().length < 3) return;
    setBusy('policy');
    setError('');
    try {
      setPolicy((await api.askAdmissionPolicy(question.trim())).data);
    } catch (err) {
      setError(apiErrorMessage(err, 'The assistant is not available right now. You can carry on without it.'));
    } finally {
      setBusy('');
    }
  };

  return (
    <Card className="p-5">
      <h2 className="flex items-center gap-2 text-base font-bold text-slate-900"><Sparkles className="h-4 w-4 text-brand-600" aria-hidden="true" />Assistant</h2>
      <p className="mt-1 text-xs text-slate-600">{AI_NOTE} Applicant details stay on the school's server.</p>
      <p className="mt-3 text-sm text-slate-800">
        {missing.length === 0 ? 'All required documents have been received.' : <><strong>Still missing:</strong> {missing.join(', ')}.</>}
      </p>
      <div className="mt-3 flex flex-wrap gap-2">
        <Button variant="secondary" disabled={Boolean(busy)} onClick={() => run('summary', () => api.getAdmissionSummary(application.id), (data) => data.summary)}>Summarise application</Button>
        <Button variant="secondary" disabled={Boolean(busy) || missing.length === 0} onClick={() => run('reminder', () => api.getAdmissionReminder(application.id, 'en'), (data) => data.draft)}>Reminder in English</Button>
        <Button variant="secondary" disabled={Boolean(busy) || missing.length === 0} onClick={() => run('reminder-ur', () => api.getAdmissionReminder(application.id, 'ur'), (data) => data.draft)}>Reminder in Urdu</Button>
      </div>
      <ErrorNotice>{error}</ErrorNotice>
      {result && (
        <Field label="Draft for your review (you can edit it)">
          {(field) => <textarea rows={8} className={`${INPUT_CLASS} mt-1`} dir={result.kind === 'reminder-ur' ? 'rtl' : 'ltr'} value={draft} onChange={(event) => setDraft(event.target.value)} {...field} />}
        </Field>
      )}
      <form onSubmit={ask} className="mt-4 space-y-2 border-t border-slate-200 pt-4">
        <TextField label="Ask about the school's admission policy" hint="Do not type a child's name here. Only the question is searched." value={question} maxLength={300} onChange={(event) => setQuestion(event.target.value)} />
        <Button type="submit" variant="secondary" disabled={busy === 'policy' || question.trim().length < 3}>{busy === 'policy' ? 'Searching…' : 'Search policies'}</Button>
      </form>
      {policy && (
        <div aria-live="polite" className="mt-3 rounded-xl bg-slate-50 p-3 text-sm text-slate-800">
          {policy.answer ? (
            <>
              <p className="whitespace-pre-wrap">{policy.answer}</p>
              {policy.sources?.length > 0 && <p className="mt-2 text-xs text-slate-600">From: {policy.sources.join(', ')}</p>}
            </>
          ) : (
            <p>{policy.message}</p>
          )}
        </div>
      )}
    </Card>
  );
}

export default function AdmissionDetail() {
  const { id } = useParams();
  const toast = useToast();
  const [version, setVersion] = useState(0);
  const { data: application, loading, error, reload } = useLoad((options) => api.getApplication(id, options), `${id}-${version}`, 'This application could not be loaded.');
  const [target, setTarget] = useState(null);
  const [dialog, setDialog] = useState('');
  const [savingDoc, setSavingDoc] = useState('');

  if (loading && !application) return <LoadingState label="Loading the application…" />;
  if (error && !application) return <ErrorState message={error} onRetry={reload} />;
  if (!application) return null;

  const refresh = () => { setTarget(null); setDialog(''); setVersion((current) => current + 1); };
  const locked = application.status === 'enrolled';

  const toggleDocument = async (item) => {
    setSavingDoc(item.name);
    try {
      await api.setApplicationDocument(application.id, { name: item.name, received: !item.received });
      setVersion((current) => current + 1);
    } catch (err) {
      toast.error(apiErrorMessage(err, 'The checklist could not be updated.'));
    } finally {
      setSavingDoc('');
    }
  };

  return (
    <div className="space-y-5">
      <PageHeader
        title={application.student_name}
        subtitle={`${application.application_number} · ${application.academic_session || ''}`}
        actions={
          <>
            <Link to="/admissions" className={buttonClass('secondary')}><ArrowLeft className="h-4 w-4" aria-hidden="true" /><span>All applications</span></Link>
            {!locked && <Link to={`/admissions/${application.id}/edit`} className={buttonClass('secondary')}><Pencil className="h-4 w-4" aria-hidden="true" /><span>Edit</span></Link>}
          </>
        }
      />

      <Card className="flex flex-wrap items-center justify-between gap-3 p-4">
        <div className="flex items-center gap-3">
          <span className="text-sm font-semibold text-slate-700">Status</span>
          <Badge tone={STATUS_TONES[application.status]}>{application.status_label}</Badge>
        </div>
        <div className="flex flex-wrap gap-2">
          {application.allowed_next_statuses.map((next) => (
            <Button key={next.value} variant={next.value === 'rejected' ? 'danger' : next.value === 'approved' ? 'success' : 'secondary'} onClick={() => setTarget(next)}>
              {next.value === 'approved' ? 'Approve' : next.value === 'rejected' ? 'Reject' : `Move to: ${next.label}`}
            </Button>
          ))}
          {application.can_enroll && (
            <Button onClick={() => setDialog('enroll')}><GraduationCap className="h-4 w-4" aria-hidden="true" /><span>Enrol student</span></Button>
          )}
        </div>
      </Card>

      {application.decision_note && (
        <Card className="p-4 text-sm text-slate-800"><strong>Decision note:</strong> {application.decision_note}<span className="text-slate-600"> — {application.decided_by}, {formatDate(application.decided_at)}</span></Card>
      )}

      {locked && (
        <Card className="space-y-3 p-5">
          <h2 className="text-base font-bold text-slate-900">Enrolled</h2>
          <p className="text-sm text-slate-700">{application.student_name} is now a student. Fees follow the normal Fees rules, and nothing has been charged automatically.</p>
          <div className="flex flex-wrap gap-2">
            <Link to={`/students/${application.student_id}`} className={buttonClass('primary')}><Banknote className="h-4 w-4" aria-hidden="true" /><span>Open student and fees</span></Link>
            <Button variant="secondary" onClick={() => setDialog('invoice')}>Create an invoice</Button>
          </div>
        </Card>
      )}

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <Card className="p-5">
          <h2 className="mb-2 text-base font-bold text-slate-900">Details</h2>
          <dl className="divide-y divide-slate-100">
            <Row label="Date of birth">{formatDate(application.dob)}</Row>
            <Row label="Gender">{application.gender}</Row>
            <Row label="Class applying for">{application.applying_grade}</Row>
            <Row label="Previous class">{application.previous_class}</Row>
            <Row label="Previous school">{application.previous_school}</Row>
            <Row label="Previous performance">{application.previous_performance}</Row>
            <Row label="Guardian">{`${application.guardian_name} (${application.guardian_relationship})`}</Row>
            <Row label="Contact">{application.phone}</Row>
            <Row label="Alternative contact">{application.alt_phone}</Row>
            <Row label="Address">{application.address}</Row>
            <Row label="Applied on">{formatDate(application.application_date)}</Row>
            <Row label="Staff notes">{application.staff_notes}</Row>
          </dl>
        </Card>

        <div className="space-y-5">
          <Card className="p-5">
            <h2 className="text-base font-bold text-slate-900">Documents</h2>
            <p className="mb-2 text-xs text-slate-600">Tick each document when it is received.</p>
            <ul>
              {application.documents.map((item) => (
                <li key={item.name}>
                  <label className="flex min-h-11 items-center gap-3 text-sm text-slate-800">
                    <input
                      type="checkbox"
                      className="h-5 w-5 rounded border-slate-300 text-brand-600 focus:ring-brand-600"
                      checked={item.received}
                      disabled={locked || savingDoc === item.name}
                      onChange={() => toggleDocument(item)}
                    />
                    <span>{item.name}</span>
                    {item.received && <Badge tone="good">Received</Badge>}
                  </label>
                </li>
              ))}
            </ul>
          </Card>

          <Card className="p-5">
            <div className="mb-2 flex items-center justify-between gap-3">
              <h2 className="text-base font-bold text-slate-900">Entry test and interview</h2>
              {!locked && <Button variant="secondary" onClick={() => setDialog('assessment')}><Plus className="h-4 w-4" aria-hidden="true" /><span>Add</span></Button>}
            </div>
            {application.assessments.length === 0 ? (
              <EmptyState icon={ClipboardCheck} title="Nothing recorded" message="An entry test or interview is optional. Add one if the school holds it." />
            ) : (
              <ul className="divide-y divide-slate-100">
                {application.assessments.map((item) => (
                  <li key={item.id} className="space-y-0.5 py-2 text-sm">
                    <p className="font-semibold text-slate-900">{item.subject} <span className="font-normal text-slate-600">· {formatDate(item.test_date)}</span></p>
                    <p className="text-slate-800">{item.obtained_marks} of {item.max_marks} marks ({item.percentage}%)</p>
                    {item.remarks && <p className="text-slate-700">Remarks: {item.remarks}</p>}
                    {item.interview_notes && <p className="text-slate-700">Interview: {item.interview_notes}</p>}
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <AssistantCard application={application} />
        <Card className="p-5">
          <h2 className="mb-2 text-base font-bold text-slate-900">History</h2>
          <ol className="space-y-3">
            {[...application.history].reverse().map((item, index) => (
              <li key={`${item.changed_at}-${index}`} className="text-sm">
                <p className="font-semibold text-slate-900">{item.to_label}</p>
                <p className="text-xs text-slate-600">{formatDate(item.changed_at)} · {item.changed_by}</p>
                {item.note && <p className="mt-0.5 text-slate-700">{item.note}</p>}
              </li>
            ))}
          </ol>
        </Card>
      </div>

      {target && <StatusDialog application={application} target={target} onClose={() => setTarget(null)} onDone={refresh} />}
      {dialog === 'assessment' && <AssessmentDialog application={application} onClose={() => setDialog('')} onDone={refresh} />}
      {dialog === 'enroll' && <EnrollDialog application={application} onClose={() => setDialog('')} onDone={refresh} />}
      {dialog === 'invoice' && <InvoiceDialog application={application} onClose={() => setDialog('')} />}
    </div>
  );
}
