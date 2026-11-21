import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { KeyRound, LogOut } from 'lucide-react';
import { api } from '../api/client';
import ChangePasswordDialog from '../components/ChangePasswordDialog';
import Button from '../components/ui/Button';
import { Badge, Card, PageHeader } from '../components/ui/Page';
import { ErrorState, LoadingState } from '../components/ui/States';
import { formatDate } from '../lib/activity';
import { classText } from '../lib/parent';
import { roleLabel } from '../lib/schoolInfo';
import { clearSession } from '../lib/session';
import { useLoad } from '../lib/useLoad';

export default function ParentProfile() {
  const navigate = useNavigate();
  const [changingPassword, setChangingPassword] = useState(false);
  const { data: parent, loading, error, reload } = useLoad(
    (options) => api.getParentProfile(options),
    'parent-profile',
    'Could not load your profile. Please try again.',
  );

  const signOut = async () => {
    try {
      await api.logout();
    } catch (requestError) {
      console.warn('Logout request did not complete:', requestError);
    }
    clearSession();
    navigate('/login');
  };

  if (loading) return <LoadingState label="Loading your profile…" />;
  if (error) return <ErrorState message={error} onRetry={reload} />;

  const rows = [
    ['Full name', parent.full_name || 'Not recorded'],
    ['Username', parent.username],
    ['Email', parent.email || 'Not recorded'],
    ['Role', roleLabel(parent.role)],
    ['Account created', formatDate(parent.created_at)],
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="My Profile"
        subtitle="These details were entered by the school office. Ask them if anything is wrong."
        actions={(
          <>
            <Button variant="secondary" onClick={() => setChangingPassword(true)}>
              <KeyRound className="h-4 w-4" aria-hidden="true" />
              <span>Change password</span>
            </Button>
            <Button variant="secondary" onClick={signOut}>
              <LogOut className="h-4 w-4" aria-hidden="true" />
              <span>Log out</span>
            </Button>
          </>
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
            <dd><Badge tone={parent.is_active ? 'good' : 'bad'}>{parent.is_active ? 'Active' : 'Deactivated'}</Badge></dd>
          </div>
        </dl>
      </Card>

      <section aria-labelledby="my-children-heading" className="space-y-2">
        <h2 id="my-children-heading" className="text-base font-bold text-slate-900">My children</h2>
        <Card>
          {parent.children.length === 0 ? (
            <p className="p-5 text-sm text-slate-600">No children are linked to your account yet. Please contact the school office.</p>
          ) : (
            <ul className="divide-y divide-slate-100">
              {parent.children.map((child) => (
                <li key={child.student_id} className="flex flex-wrap items-center justify-between gap-2 p-4 text-sm">
                  <div>
                    <p className="font-semibold text-slate-900">{child.name}</p>
                    <p className="text-xs text-slate-600">{classText(child)} &bull; Roll #{child.roll_number}</p>
                  </div>
                  {child.relationship && <Badge tone="info">{child.relationship}</Badge>}
                </li>
              ))}
            </ul>
          )}
        </Card>
      </section>

      {changingPassword && <ChangePasswordDialog onClose={() => setChangingPassword(false)} />}
    </div>
  );
}
