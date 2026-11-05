import React, { useState } from 'react';
import { ClipboardCheck, Sparkles } from 'lucide-react';
import client from '../api/client';
import Button from '../components/ui/Button';
import { SelectField, TextField } from '../components/ui/Field';
import { Card, PageHeader } from '../components/ui/Page';
import { EmptyState, ErrorNotice, LoadingState } from '../components/ui/States';
import { apiErrorMessage } from '../lib/errors';

const GRADE_OPTIONS = [
  { value: '', label: 'Select a grade' },
  ...['Grade 6', 'Grade 7', 'Grade 8', 'Grade 9', 'Grade 10'].map((grade) => ({ value: grade, label: grade })),
];

export default function Admissions() {
  const [rollNumber, setRollNumber] = useState('');
  const [program, setProgram] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setResult(null);
    setError('');

    try {
      const response = await client.post('/api/admissions-crew/evaluate', {
        student_roll_number: rollNumber,
        desired_program: program,
      });
      const data = response.data;
      // The service sometimes returns an object with a 'raw' property instead of a plain string.
      setResult({
        student: data.student_name || rollNumber,
        text: data.recommendation?.raw || data.recommendation || 'No recommendation was returned.',
      });
    } catch (err) {
      setError(apiErrorMessage(err, 'The admissions check could not be completed. Please try again.'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-5">
      <PageHeader title="Admissions" subtitle="An AI suggestion on a student's eligibility, from their school records. Staff make the decision." />

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <Card className="p-5">
          <h2 className="mb-4 text-base font-bold text-slate-900">Check eligibility</h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            <SelectField label="Grade applied for" required options={GRADE_OPTIONS} value={program} onChange={(e) => setProgram(e.target.value)} />
            <TextField label="Student's roll number" required value={rollNumber} onChange={(e) => setRollNumber(e.target.value)} />
            <Button type="submit" disabled={loading} className="w-full">
              <Sparkles className="h-4 w-4" aria-hidden="true" />
              <span>{loading ? 'Checking…' : 'Check Eligibility'}</span>
            </Button>
          </form>
        </Card>

        <Card className="flex min-h-72 flex-col p-5">
          <h2 className="mb-3 text-base font-bold text-slate-900">AI suggestion</h2>
          <div aria-live="polite" className="flex-1">
            <ErrorNotice>{error}</ErrorNotice>
            {loading && <LoadingState label="Reading the student's records. This can take a minute." />}
            {!loading && !error && !result && (
              <EmptyState icon={ClipboardCheck} title="Nothing checked yet" message="Enter a grade and roll number to get a suggestion." />
            )}
            {result && (
              <div className="space-y-3 text-sm text-slate-800">
                <p className="font-semibold">{result.student}</p>
                <p className="whitespace-pre-wrap leading-relaxed">{result.text}</p>
                <p className="border-t border-slate-200 pt-3 text-xs text-slate-600">An AI suggestion, which can be wrong. Please check the student's records before deciding.</p>
              </div>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}
