import React, { useState } from 'react';
import { api } from '../api/client';
import { apiErrorMessage } from '../lib/errors';
import Button from './ui/Button';
import { SelectField, TextField } from './ui/Field';
import Modal from './ui/Modal';
import { ErrorNotice } from './ui/States';

export const GRADES = ['Grade 6', 'Grade 7', 'Grade 8', 'Grade 9', 'Grade 10'];
export const SECTIONS = ['A', 'B'];

const GRADE_OPTIONS = GRADES.map((grade) => ({ value: grade, label: grade }));
const SECTION_OPTIONS = SECTIONS.map((section) => ({ value: section, label: `Section ${section}` }));
const EMPTY_FORM = { name: '', roll_number: '', grade: 'Grade 8', section: 'A', guardian_name: '', phone: '', dob: '' };
const FORM_ID = 'student-form';

/** Adds a student, or edits one when `student` is given. `onSaved` receives a message to show. */
export default function StudentFormDialog({ student, onClose, onSaved }) {
  const [form, setForm] = useState(student ? {
    name: student.name,
    roll_number: student.roll_number,
    grade: student.grade,
    section: student.section,
    guardian_name: student.guardian_name,
    phone: student.phone,
    dob: student.dob || '',
  } : EMPTY_FORM);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const field = (key) => ({ value: form[key], onChange: (event) => setForm({ ...form, [key]: event.target.value }) });

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setSaving(true);
    try {
      if (student) await api.updateStudent(student.id, form);
      else await api.createStudent(form);
      onSaved(student ? `${form.name}'s record was updated.` : `${form.name} was added.`);
    } catch (err) {
      setError(apiErrorMessage(err, 'The student could not be saved. Please try again.'));
      setSaving(false);
    }
  };

  return (
    <Modal
      title={student ? `Edit ${student.name}` : 'Add Student'}
      size="lg"
      busy={saving}
      onClose={onClose}
      footer={(
        <>
          <Button variant="ghost" onClick={onClose} disabled={saving}>Cancel</Button>
          <Button type="submit" form={FORM_ID} disabled={saving}>{saving ? 'Saving…' : 'Save Student'}</Button>
        </>
      )}
    >
      <ErrorNotice>{error}</ErrorNotice>
      <form id={FORM_ID} onSubmit={handleSubmit} className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <TextField label="Full name" required {...field('name')} />
        <TextField label="Roll number" required hint="Letters, numbers, / and -" {...field('roll_number')} />
        <SelectField label="Grade" options={GRADE_OPTIONS} {...field('grade')} />
        <SelectField label="Section" options={SECTION_OPTIONS} {...field('section')} />
        <TextField label="Guardian name" required {...field('guardian_name')} />
        <TextField label="Contact phone" type="tel" required hint="For example 0300-1234567" {...field('phone')} />
        <TextField label="Date of birth (optional)" type="date" {...field('dob')} />
      </form>
    </Modal>
  );
}
