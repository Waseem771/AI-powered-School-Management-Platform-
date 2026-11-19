import React from 'react';
import { CalendarCheck, ClipboardList, GraduationCap, Users } from 'lucide-react';
import { api } from '../api/client';
import { Badge, Card, PageHeader } from '../components/ui/Page';
import { ErrorState, LoadingState } from '../components/ui/States';
import { useLoad } from '../lib/useLoad';
import { roleLabel } from '../lib/schoolInfo';

// Features that do not exist yet. They are labelled as such and cannot be opened.
const COMING_SOON = [
  { title: 'My Classes', note: 'Coming in Phase 2', icon: Users },
  { title: 'Daily Attendance', note: 'Coming in Phase 2', icon: CalendarCheck },
  { title: 'Student Records', note: 'Coming later', icon: ClipboardList },
  { title: 'Marks Entry', note: 'Coming later', icon: GraduationCap },
];

export function AccountStatus({ active }) {
  return <Badge tone={active ? 'good' : 'bad'}>{active ? 'Active' : 'Deactivated'}</Badge>;
}

export default function TeacherDashboard() {
  const { data: teacher, loading, error, reload } = useLoad(
    (options) => api.getTeacherProfile(options),
    'teacher-profile',
    'Could not load your account. Please try again.',
  );

  if (loading) return <LoadingState label="Loading your portal…" />;
  if (error) return <ErrorState message={error} onRetry={reload} />;

  const name = teacher.full_name || teacher.username;

  return (
    <div className="space-y-6">
      <PageHeader title="Teacher Dashboard" subtitle={`Welcome, ${name}.`} />

      <Card className="p-5">
        <h2 className="text-base font-bold text-slate-900">Your account</h2>
        <dl className="mt-3 grid gap-4 text-sm sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <dt className="text-xs font-semibold text-slate-600">Name</dt>
            <dd className="mt-0.5 text-slate-900">{name}</dd>
          </div>
          <div>
            <dt className="text-xs font-semibold text-slate-600">{teacher.email ? 'Email' : 'Username'}</dt>
            <dd className="mt-0.5 break-all text-slate-900">{teacher.email || teacher.username}</dd>
          </div>
          <div>
            <dt className="text-xs font-semibold text-slate-600">Role</dt>
            <dd className="mt-0.5 text-slate-900">{roleLabel(teacher.role)}</dd>
          </div>
          <div>
            <dt className="text-xs font-semibold text-slate-600">Account status</dt>
            <dd className="mt-0.5"><AccountStatus active={teacher.is_active} /></dd>
          </div>
        </dl>
      </Card>

      <section aria-labelledby="coming-soon-heading">
        <h2 id="coming-soon-heading" className="mb-3 text-base font-bold text-slate-900">Coming soon</h2>
        <ul className="grid gap-4 sm:grid-cols-2">
          {COMING_SOON.map(({ title, note, icon: Icon }) => (
            <li key={title}>
              <div aria-disabled="true" className="flex items-center gap-3 rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-4 text-slate-600">
                <Icon className="h-6 w-6 shrink-0 text-slate-400" aria-hidden="true" />
                <div>
                  <p className="text-sm font-semibold text-slate-800">{title}</p>
                  <p className="text-xs text-slate-600">{note}</p>
                </div>
              </div>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
