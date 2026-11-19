import React, { useState } from 'react';
import { KeyRound } from 'lucide-react';
import { api } from '../api/client';
import ChangePasswordDialog from '../components/ChangePasswordDialog';
import Button from '../components/ui/Button';
import { Card, PageHeader } from '../components/ui/Page';
import { ErrorState, LoadingState } from '../components/ui/States';
import { formatDate } from '../lib/activity';
import { roleLabel } from '../lib/schoolInfo';
import { useLoad } from '../lib/useLoad';
import { AccountStatus } from './TeacherDashboard';

export default function TeacherProfile() {
  const [changingPassword, setChangingPassword] = useState(false);
  const { data: teacher, loading, error, reload } = useLoad(
    (options) => api.getTeacherProfile(options),
    'teacher-profile',
    'Could not load your profile. Please try again.',
  );

  if (loading) return <LoadingState label="Loading your profile…" />;
  if (error) return <ErrorState message={error} onRetry={reload} />;

  const rows = [
    ['Full name', teacher.full_name || 'Not recorded'],
    ['Username', teacher.username],
    ['Email', teacher.email || 'Not recorded'],
    ['Role', roleLabel(teacher.role)],
    ['Account created', formatDate(teacher.created_at)],
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="My Profile"
        subtitle="These details were entered by the school office. Ask them if anything is wrong."
        actions={(
          <Button variant="secondary" onClick={() => setChangingPassword(true)}>
            <KeyRound className="h-4 w-4" aria-hidden="true" />
            <span>Change password</span>
          </Button>
        )}
      />
      <Card className="p-5">
        <dl className="divide-y divide-slate-100 text-sm">
          {rows.map(([label, value]) => (
            <div key={label} className="flex flex-col gap-0.5 py-3 sm:flex-row sm:items-baseline sm:gap-4">
              <dt className="w-40 shrink-0 text-xs font-semibold text-slate-600">{label}</dt>
              <dd className="min-w-0 break-all text-slate-900">{value}</dd>
            </div>
          ))}
          <div className="flex flex-col gap-0.5 py-3 sm:flex-row sm:items-center sm:gap-4">
            <dt className="w-40 shrink-0 text-xs font-semibold text-slate-600">Account status</dt>
            <dd><AccountStatus active={teacher.is_active} /></dd>
          </div>
        </dl>
      </Card>
      {changingPassword && <ChangePasswordDialog onClose={() => setChangingPassword(false)} />}
    </div>
  );
}
