import React, { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { api } from '../api/client';
import Button, { buttonClass } from '../components/ui/Button';
import { Field, INPUT_CLASS, SelectField, TextField } from '../components/ui/Field';
import { Card, PageHeader } from '../components/ui/Page';
import { ErrorNotice, ErrorState, LoadingState } from '../components/ui/States';
import { useToast } from '../components/ui/Toast';
import { EMPTY_APPLICATION, applicationPayload, applicationProblems, isoToday } from '../lib/admissions';
import { apiErrorMessage } from '../lib/errors';
import { useLoad } from '../lib/useLoad';

const OPTIONAL = '(optional)';

function Section({ title, hint, children }) {
  return (
    <Card className="p-5">
      <h2 className="text-base font-bold text-slate-900">{title}</h2>
      {hint && <p className="mb-3 mt-0.5 text-sm text-slate-600">{hint}</p>}
      <div className="mt-3 grid grid-cols-1 gap-4 md:grid-cols-2">{children}</div>
    </Card>
  );
}

/** Shows the field's problem under it once the form has been tried. */
function Checked({ problem, children }) {
  return (
    <div>
      {children}
      {problem && <p role="alert" className="mt-1 text-xs font-semibold text-rose-700">{problem}</p>}
    </div>
  );
}

export default function AdmissionForm() {
  const { id } = useParams();
  const editing = Boolean(id);
  const navigate = useNavigate();
  const toast = useToast();
  const meta = useLoad((options) => api.getAdmissionOptions(options), 'options', 'The form could not be loaded.');
  const existing = useLoad(
    (options) => (editing ? api.getApplication(id, options) : Promise.resolve({ data: null })),
    `existing-${id || 'new'}`,
    'This application could not be loaded.',
  );

  const [form, setForm] = useState(EMPTY_APPLICATION);
  const [received, setReceived] = useState([]);
  const [academicYearId, setAcademicYearId] = useState('');
  const [tried, setTried] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (existing.data) {
      const next = { ...EMPTY_APPLICATION };
      Object.keys(next).forEach((key) => { next[key] = existing.data[key] ?? ''; });
      setForm(next);
    }
  }, [existing.data]);

  const problems = applicationProblems(form);
  const shown = tried ? problems : {};
  const set = (name) => (event) => setForm((current) => ({ ...current, [name]: event.target.value }));
  const textProps = (name) => ({ value: form[name], onChange: set(name), 'aria-invalid': Boolean(shown[name]) || undefined });

  const submit = async (event) => {
    event.preventDefault();
    setTried(true);
    setError('');
    if (Object.keys(problems).length > 0) {
      setError('Please correct the highlighted fields.');
      return;
    }
    setSaving(true);
    try {
      const payload = applicationPayload(form);
      if (editing) {
        await api.updateApplication(id, payload);
        toast.success('Application updated.');
        navigate(`/admissions/${id}`);
      } else {
        if (academicYearId) payload.academic_year_id = Number(academicYearId);
        payload.application_date = isoToday();
        payload.documents_received = received;
        const response = await api.createApplication(payload);
        toast.success(`Application ${response.data.application_number} created.`);
        navigate(`/admissions/${response.data.id}`);
      }
    } catch (err) {
      setError(apiErrorMessage(err, 'The application could not be saved. Please try again.'));
    } finally {
      setSaving(false);
    }
  };

  if (meta.loading || existing.loading) return <LoadingState label="Loading the form…" />;
  if (meta.error) return <ErrorState message={meta.error} onRetry={meta.reload} />;
  if (existing.error) return <ErrorState message={existing.error} onRetry={existing.reload} />;
  const options = meta.data;
  const currentYear = options.academic_years.find((year) => year.is_current);

  return (
    <form onSubmit={submit} noValidate className="space-y-5">
      <PageHeader
        title={editing ? 'Edit application' : 'New application'}
        subtitle={editing ? existing.data?.application_number : 'Fields marked * are required. Everything else may be left blank.'}
        actions={<Link to={editing ? `/admissions/${id}` : '/admissions'} className={buttonClass('secondary')}><ArrowLeft className="h-4 w-4" aria-hidden="true" /><span>Back</span></Link>}
      />

      <ErrorNotice>{error}</ErrorNotice>

      <Section title="Student">
        <Checked problem={shown.student_name}><TextField label="Full name *" autoComplete="off" {...textProps('student_name')} /></Checked>
        <Checked problem={shown.dob}><Field label="Date of birth *">{(field) => <input type="date" className={INPUT_CLASS} {...field} {...textProps('dob')} max={isoToday()} />}</Field></Checked>
        <SelectField label={`Gender ${OPTIONAL}`} {...textProps('gender')} options={[{ value: '', label: 'Not stated' }, ...options.genders.map((value) => ({ value, label: value }))]} />
        <Checked problem={shown.applying_grade}>
          <SelectField label="Class applying for *" {...textProps('applying_grade')} options={[{ value: '', label: 'Select a class' }, ...options.grades.map((value) => ({ value, label: value }))]} />
        </Checked>
        <TextField label={`Previous class ${OPTIONAL}`} {...textProps('previous_class')} />
        <TextField label={`Previous school ${OPTIONAL}`} {...textProps('previous_school')} />
        <div className="md:col-span-2">
          <TextField label={`Previous academic performance ${OPTIONAL}`} hint="For example: 72% in the last annual exam, as reported by the family." {...textProps('previous_performance')} />
        </div>
      </Section>

      <Section title="Parent or guardian">
        <Checked problem={shown.guardian_name}><TextField label="Father or guardian name *" autoComplete="off" {...textProps('guardian_name')} /></Checked>
        <SelectField label="Relationship *" {...textProps('guardian_relationship')} options={options.relationships.map((value) => ({ value, label: value }))} />
        <Checked problem={shown.phone}><TextField label="Contact number *" type="tel" inputMode="tel" hint="For example 0300-1234567" {...textProps('phone')} /></Checked>
        <Checked problem={shown.alt_phone}><TextField label={`Alternative number ${OPTIONAL}`} type="tel" inputMode="tel" {...textProps('alt_phone')} /></Checked>
        <div className="md:col-span-2">
          <Checked problem={shown.address}><TextField label="Home address *" {...textProps('address')} /></Checked>
        </div>
      </Section>

      <Section title="Application" hint="The application number is created when you save.">
        {!editing && (
          <>
            <SelectField
              label="Academic session"
              value={academicYearId}
              onChange={(event) => setAcademicYearId(event.target.value)}
              options={[{ value: '', label: currentYear ? `${currentYear.label} (current)` : 'Current session' }, ...options.academic_years.filter((year) => !year.is_current).map((year) => ({ value: String(year.id), label: year.label }))]}
            />
            <TextField label="Application date" value={isoToday()} readOnly hint="Today's date." />
            <fieldset className="md:col-span-2">
              <legend className="mb-1 text-sm font-semibold text-slate-700">Documents handed in {OPTIONAL}</legend>
              <p className="mb-2 text-xs text-slate-600">Tick what the family has already brought. The rest can be ticked off later.</p>
              <div className="grid grid-cols-1 gap-1 sm:grid-cols-2">
                {options.documents.map((name) => (
                  <label key={name} className="flex min-h-11 items-center gap-2 text-sm text-slate-800">
                    <input
                      type="checkbox"
                      className="h-5 w-5 rounded border-slate-300 text-brand-600 focus:ring-brand-600"
                      checked={received.includes(name)}
                      onChange={(event) => setReceived((current) => (event.target.checked ? [...current, name] : current.filter((item) => item !== name)))}
                    />
                    {name}
                  </label>
                ))}
              </div>
            </fieldset>
          </>
        )}
        <div className="md:col-span-2">
          <Field label={`Staff notes ${OPTIONAL}`} hint="Internal. Not shared with the family.">
            {(field) => <textarea rows={3} maxLength={1000} className={INPUT_CLASS} {...field} {...textProps('staff_notes')} />}
          </Field>
        </div>
      </Section>

      <div className="flex flex-wrap justify-end gap-2">
        <Link to={editing ? `/admissions/${id}` : '/admissions'} className={buttonClass('secondary')}>Cancel</Link>
        <Button type="submit" disabled={saving}>{saving ? 'Saving…' : editing ? 'Save changes' : 'Create application'}</Button>
      </div>
    </form>
  );
}
