import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { CheckCircle2, ClipboardList, Clock, Eye, FileSearch, GraduationCap, Plus, Users, XCircle } from 'lucide-react';
import { api } from '../api/client';
import DataTable from '../components/DataTable';
import StatCard from '../components/StatCard';
import { buttonClass } from '../components/ui/Button';
import { SearchInput, SelectField } from '../components/ui/Field';
import { Badge, Card, PageHeader } from '../components/ui/Page';
import { ErrorNotice } from '../components/ui/States';
import { STATUS_TONES } from '../lib/admissions';
import { formatDate } from '../lib/activity';
import { useLoad } from '../lib/useLoad';

const PAGE_SIZE = 25;

export default function Admissions() {
  const [search, setSearch] = useState('');
  const [debounced, setDebounced] = useState('');
  const [status, setStatus] = useState('');
  const [grade, setGrade] = useState('');
  const [page, setPage] = useState(1);

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(search.trim()), 300);
    return () => clearTimeout(timer);
  }, [search]);
  useEffect(() => setPage(1), [debounced, status, grade]);

  const stats = useLoad((options) => api.getAdmissionStats(options), 'stats', 'The counts could not be loaded.');
  const meta = useLoad((options) => api.getAdmissionOptions(options), 'options', 'The form options could not be loaded.');
  const list = useLoad(
    (options) => api.getApplications({ search: debounced || undefined, status: status || undefined, grade: grade || undefined, page, page_size: PAGE_SIZE }, options),
    `${debounced}|${status}|${grade}|${page}`,
    'Applications could not be loaded.',
  );

  const counts = stats.data;
  const rows = list.data?.items || [];
  const total = list.data?.total || 0;
  const lastPage = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const filtering = Boolean(debounced || status || grade);

  const columns = [
    {
      header: 'Applicant',
      mobile: 'title',
      render: (row) => (
        <div>
          <Link to={`/admissions/${row.id}`} className="inline-flex min-h-11 items-center font-semibold text-slate-900 underline-offset-2 hover:underline">{row.student_name}</Link>
          <p className="text-xs text-slate-600">{row.application_number}</p>
        </div>
      ),
    },
    { header: 'Class', render: (row) => row.applying_grade },
    { header: 'Guardian', render: (row) => row.guardian_name },
    { header: 'Applied', render: (row) => formatDate(row.application_date) },
    { header: 'Status', render: (row) => <Badge tone={STATUS_TONES[row.status]}>{row.status_label}</Badge> },
    {
      header: 'Actions',
      mobile: 'actions',
      render: (row) => (
        <>
          <Link to={`/admissions/${row.id}`} className={buttonClass('secondary')} aria-label={`View ${row.student_name}`}>
            <Eye className="h-4 w-4" aria-hidden="true" />
            <span>{row.status === 'enrolled' || row.status === 'rejected' ? 'View' : 'Process'}</span>
          </Link>
          {row.status !== 'enrolled' && (
            <Link to={`/admissions/${row.id}/edit`} className={buttonClass('ghost')} aria-label={`Edit ${row.student_name}`}>Edit</Link>
          )}
        </>
      ),
    },
  ];

  return (
    <div className="space-y-5">
      <PageHeader
        title="Admissions"
        subtitle="New student applications, from first enquiry to enrolment. Staff make every decision."
        actions={
          <Link to="/admissions/new" className={buttonClass('primary')}>
            <Plus className="h-4 w-4" aria-hidden="true" />
            <span>New application</span>
          </Link>
        }
      />

      <ErrorNotice>{stats.error}</ErrorNotice>
      <section aria-label="Admissions overview" className="grid grid-cols-2 gap-3 lg:grid-cols-6">
        <StatCard title="Total" value={counts ? counts.total : '…'} icon={Users} />
        <StatCard title="Pending" value={counts ? counts.new : '…'} subtitle="Not yet reviewed" icon={ClipboardList} color="blue" />
        <StatCard title="Under review" value={counts ? counts.under_review + counts.test_interview : '…'} subtitle="Including tests" icon={Clock} color="amber" />
        <StatCard title="Approved" value={counts ? counts.approved : '…'} subtitle="Ready to enrol" icon={CheckCircle2} color="green" />
        <StatCard title="Rejected" value={counts ? counts.rejected : '…'} icon={XCircle} color="red" />
        <StatCard title="Enrolled" value={counts ? counts.enrolled : '…'} icon={GraduationCap} color="green" />
      </section>

      <Card>
        <div className="grid grid-cols-1 gap-3 border-b border-slate-200 p-4 md:grid-cols-[1fr_12rem_12rem]">
          <SearchInput label="Search name, number, guardian or phone" value={search} onChange={(event) => setSearch(event.target.value)} />
          <SelectField
            label="Status"
            value={status}
            onChange={(event) => setStatus(event.target.value)}
            options={[{ value: '', label: 'All statuses' }, ...(meta.data?.statuses || []).map((item) => ({ value: item.value, label: item.label }))]}
          />
          <SelectField
            label="Class"
            value={grade}
            onChange={(event) => setGrade(event.target.value)}
            options={[{ value: '', label: 'All classes' }, ...(meta.data?.grades || []).map((item) => ({ value: item, label: item }))]}
          />
        </div>
        <DataTable
          columns={columns}
          rows={rows}
          loading={list.loading}
          error={list.error}
          onRetry={list.reload}
          loadingLabel="Loading applications…"
          emptyState={
            filtering
              ? { icon: FileSearch, title: 'No applications match', message: 'Try a different search or clear the filters.' }
              : {
                  icon: ClipboardList,
                  title: 'No applications yet',
                  message: 'Add the first application when a family enquires.',
                  action: <Link to="/admissions/new" className={buttonClass('primary')}>New application</Link>,
                }
          }
        />
        {total > PAGE_SIZE && (
          <nav aria-label="Pages" className="flex items-center justify-between gap-3 border-t border-slate-200 p-3 text-sm text-slate-700">
            <button type="button" className={buttonClass('secondary')} disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</button>
            <span>Page {page} of {lastPage} · {total} applications</span>
            <button type="button" className={buttonClass('secondary')} disabled={page >= lastPage} onClick={() => setPage(page + 1)}>Next</button>
          </nav>
        )}
      </Card>
    </div>
  );
}
