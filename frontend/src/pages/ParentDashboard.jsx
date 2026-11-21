import React from 'react';
import { Link } from 'react-router-dom';
import { CalendarCheck, GraduationCap, Receipt } from 'lucide-react';
import { api } from '../api/client';
import StatCard from '../components/StatCard';
import { Badge, Card, PageHeader } from '../components/ui/Page';
import { EmptyState, ErrorState, LoadingState } from '../components/ui/States';
import { buttonClass } from '../components/ui/Button';
import { formatRupees } from '../lib/fees';
import {
  classText, feeLine, feeTone, latestResultLine, monthTitle, rateLine, rateTone,
} from '../lib/parent';
import { useLoad } from '../lib/useLoad';

function Line({ icon: Icon, label, children }) {
  return (
    <div className="flex items-start gap-3">
      <Icon className="mt-0.5 h-5 w-5 shrink-0 text-brand-600" aria-hidden="true" />
      <div className="min-w-0">
        <p className="text-xs font-semibold text-slate-600">{label}</p>
        <div className="text-sm text-slate-900">{children}</div>
      </div>
    </div>
  );
}

function ChildCard({ child, month }) {
  const monthly = child.attendance.month_summary;
  const session = child.attendance.session_summary;
  const open = (page) => `/parent/${page}?child=${child.id}`;

  return (
    <Card className="p-5">
      <article aria-label={child.name}>
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <h2 className="text-lg font-bold text-navy-900">{child.name}</h2>
            <p className="text-sm text-slate-600">
              {classText(child)} &bull; Roll #{child.roll_number}
              {child.relationship ? <> &bull; You: {child.relationship}</> : null}
            </p>
          </div>
          {!child.enrolled && <Badge tone="warn">No longer enrolled</Badge>}
        </div>

        <div className="mt-4 grid gap-4 sm:grid-cols-3">
          <Line icon={CalendarCheck} label={`Attendance, ${monthTitle(month)}`}>
            <Badge tone={rateTone(monthly.attendance_rate)}>{rateLine(monthly, 'this month')}</Badge>
            <p className="mt-1 text-xs text-slate-600">{rateLine(session, 'this session')}</p>
          </Line>
          <Line icon={GraduationCap} label="Latest result">
            {latestResultLine(child.latest_result)}
            {child.latest_result && <p className="mt-1 text-xs text-slate-600">Grade {child.latest_result.grade}</p>}
          </Line>
          <Line icon={Receipt} label="Fees">
            <Badge tone={feeTone(child.fees)}>{feeLine(child.fees)}</Badge>
            {child.fees.overdue > 0 && <p className="mt-1 text-xs font-semibold text-rose-800">{formatRupees(child.fees.overdue)} overdue</p>}
          </Line>
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          <Link to={open('attendance')} className={buttonClass('secondary')}>
            Attendance<span className="sr-only"> for {child.name}</span>
          </Link>
          <Link to={open('results')} className={buttonClass('secondary')}>
            Results<span className="sr-only"> for {child.name}</span>
          </Link>
          <Link to={open('fees')} className={buttonClass('secondary')}>
            Fees<span className="sr-only"> for {child.name}</span>
          </Link>
        </div>
      </article>
    </Card>
  );
}

export default function ParentDashboard() {
  const { data, loading, error, reload } = useLoad(
    (options) => api.getParentChildren(options),
    'parent-children',
    'Could not load your dashboard. Please try again.',
  );

  if (loading) return <LoadingState label="Loading your dashboard…" />;
  if (error) return <ErrorState message={error} onRetry={reload} />;

  const name = data.parent.full_name || data.parent.username;
  const { children, totals } = data;

  return (
    <div className="space-y-6">
      <PageHeader title="Parent Dashboard" subtitle={`Welcome, ${name}.`} />

      {children.length === 0 ? (
        <Card>
          <EmptyState
            title="No children are linked to your account yet"
            message="Please contact the school office, and they will link your child to this account."
          />
        </Card>
      ) : (
        <>
          <section aria-label="Fees for all your children" className="grid gap-4 sm:grid-cols-3">
            <StatCard title="Your children" value={children.length} subtitle="Linked to this account" icon={GraduationCap} />
            <StatCard
              title="Fees to pay"
              value={formatRupees(totals.outstanding)}
              subtitle={totals.outstanding === 0 ? 'Nothing is due' : 'Across all your children'}
              icon={Receipt}
              color={totals.outstanding > 0 ? 'amber' : 'green'}
            />
            <StatCard
              title="Overdue"
              value={formatRupees(totals.overdue)}
              subtitle={totals.overdue === 0 ? 'Nothing is overdue' : 'Please pay at the school office'}
              icon={Receipt}
              color={totals.overdue > 0 ? 'red' : 'green'}
            />
          </section>
          <section aria-label="Your children" className="space-y-4">
            {children.map((child) => <ChildCard key={child.id} child={child} month={data.month} />)}
          </section>
        </>
      )}
    </div>
  );
}
