import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Users,
  AlertOctagon,
  Bot,
  ArrowUpRight,
  CheckCircle2,
  Clock
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend
} from 'recharts';
import { api } from '../api/client';
import { MODEL_NOTE } from '../lib/risk';
import { apiErrorMessage } from '../lib/errors';
import { countLabel } from '../lib/uiState';
import StatCard from '../components/StatCard';
import { buttonClass } from '../components/ui/Button';
import { Card, PageHeader } from '../components/ui/Page';
import { EmptyState, ErrorState, LoadingState } from '../components/ui/States';

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    fetchDashboardStats(controller.signal);
    return () => controller.abort();
  }, []);

  const fetchDashboardStats = async (signal) => {
    try {
      setError('');
      setLoading(true);
      const res = await api.getDashboardStats({ signal });
      setStats(res.data);
    } catch (err) {
      if (err.code === 'ERR_CANCELED') return;
      setError(apiErrorMessage(err, 'The dashboard could not be loaded. Please try again.'));
    } finally {
      // A cancelled request has a newer one behind it, so the page stays in its loading state.
      if (!signal?.aborted) setLoading(false);
    }
  };

  if (loading) {
    return <LoadingState label="Loading the dashboard…" />;
  }

  if (error) {
    return <Card><ErrorState title="The dashboard could not be loaded" message={error} onRetry={() => fetchDashboardStats()} /></Card>;
  }

  const kpis = stats?.kpis || {};
  const feeSummary = stats?.fee_summary || [];
  const gradeData = stats?.grade_distribution || [];
  const subjectAverages = stats?.subject_performance || [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Dashboard"
        subtitle="Students, fees, and exam results at a glance."
        actions={(
          <>
            <Link to="/students" className={buttonClass('secondary')}><Users className="h-4 w-4" aria-hidden="true" /><span>Students</span></Link>
            <Link to="/chatbot" className={buttonClass('primary')}><Bot className="h-4 w-4" aria-hidden="true" /><span>Ask the Assistant</span></Link>
          </>
        )}
      />

      {/* Top 4 KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Current students"
          value={kpis.total_students ?? 0}
          icon={Users}
          color="blue"
        />
        <StatCard
          title="Fees collected"
          value={`Rs. ${(kpis.total_collected || 0).toLocaleString()}`}
          subtitle={`${kpis.collection_rate || 0}% of the amount billed`}
          icon={CheckCircle2}
          color="green"
        />
        <StatCard
          title="Fees still owed"
          value={`Rs. ${(kpis.total_pending || 0).toLocaleString()}`}
          subtitle={`Rs. ${(kpis.total_overdue || 0).toLocaleString()} overdue`}
          icon={Clock}
          color="amber"
        />
        <StatCard
          title="High academic estimate"
          value={countLabel(kpis.at_risk_students || 0, 'student')}
          subtitle="For teacher review"
          icon={AlertOctagon}
          color="red"
        />
      </div>

      {/* Analytics Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Grade Distribution Bar Chart */}
        <div className="lg:col-span-2 bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-base font-bold text-slate-900">Students by grade</h2>
              <p className="text-sm text-slate-600">Current students only</p>
            </div>
          </div>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={gradeData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" />
                <XAxis dataKey="grade" tick={{ fontSize: 11, fill: '#64748B' }} />
                <YAxis tick={{ fontSize: 11, fill: '#64748B' }} allowDecimals={false} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0F172A', borderRadius: '8px', color: '#FFF', fontSize: '12px', border: 'none' }}
                />
                <Bar dataKey="count" name="Students" fill="#2563eb" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Fee Collection Donut Chart */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs flex flex-col justify-between">
          <div>
            <h2 className="text-base font-bold text-slate-900">Fees collected and owed</h2>
            <p className="text-sm text-slate-600">All challans issued</p>
          </div>
          <div className="h-52 w-full my-2">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={feeSummary}
                  cx="50%"
                  cy="50%"
                  innerRadius={55}
                  outerRadius={75}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {feeSummary.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(val) => `Rs. ${val.toLocaleString()}`}
                  contentStyle={{ backgroundColor: '#0F172A', borderRadius: '8px', color: '#FFF', fontSize: '12px', border: 'none' }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="space-y-2 border-t border-slate-100 pt-3">
            <div className="flex items-center justify-between text-xs">
              <span className="flex items-center gap-1.5 text-slate-600">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
                <span>Collected:</span>
              </span>
              <span className="font-bold text-slate-800">Rs. {(kpis.total_collected || 0).toLocaleString()}</span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="flex items-center gap-1.5 text-slate-600">
                <span className="w-2.5 h-2.5 rounded-full bg-rose-500"></span>
                <span>Still owed:</span>
              </span>
              <span className="font-bold text-slate-800">Rs. {(kpis.total_pending || 0).toLocaleString()}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Row 2: Subject Performance & AI At-Risk Callout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Subject Performance */}
        <div className="lg:col-span-2 bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-base font-bold text-slate-900">Average marks by subject</h2>
              <p className="text-sm text-slate-600">Each student's latest exam</p>
            </div>
          </div>
          {subjectAverages.length === 0 ? (
            <EmptyState title="No marks yet" message="Subject averages appear once marks are entered." />
          ) : (
          <div className="h-60 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={subjectAverages} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" />
                <XAxis dataKey="subject" tick={{ fontSize: 10, fill: '#64748B' }} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: '#64748B' }} />
                <Tooltip
                  formatter={(val) => `${val}%`}
                  contentStyle={{ backgroundColor: '#0F172A', borderRadius: '8px', color: '#FFF', fontSize: '12px', border: 'none' }}
                />
                <Bar dataKey="average" name="Average %" fill="#06b6d4" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          )}
        </div>

        {/* AI Early Warning Banner Card */}
        <div className="flex flex-col justify-between rounded-2xl bg-navy-900 p-6 text-white shadow-sm">
          <div>
            <p className="mb-2 text-xs font-semibold text-accent-300">Estimate for teacher review</p>
            <h2 className="text-xl font-bold text-white">Academic Early Warning</h2>
            <p className="mt-2 text-sm leading-relaxed text-slate-200">
              From exam marks only. {MODEL_NOTE}
            </p>

            <div className="mt-5 space-y-2">
              <div className="flex items-center justify-between text-xs bg-white/10 px-3 py-2 rounded-xl">
                <span className="text-rose-300 font-semibold">&bull; High:</span>
                <span className="font-bold text-white">{countLabel(kpis.at_risk_students || 0, 'student')}</span>
              </div>
              <div className="flex items-center justify-between text-xs bg-white/10 px-3 py-2 rounded-xl">
                <span className="text-amber-300 font-semibold">&bull; Medium:</span>
                <span className="font-bold text-white">{countLabel(kpis.medium_risk_students || 0, 'student')}</span>
              </div>
              <div className="flex items-center justify-between text-xs bg-white/10 px-3 py-2 rounded-xl">
                <span className="text-emerald-300 font-semibold">&bull; Low:</span>
                <span className="font-bold text-white">{countLabel(kpis.low_risk_students || 0, 'student')}</span>
              </div>
              <div className="flex items-center justify-between text-xs bg-white/10 px-3 py-2 rounded-xl">
                <span className="text-slate-300 font-semibold">&bull; Not enough data:</span>
                <span className="font-bold text-white">{countLabel(kpis.not_enough_data_students || 0, 'student')}</span>
              </div>
              <div className="flex items-center justify-between text-xs border border-white/20 px-3 py-2 rounded-xl">
                <span className="text-slate-300 font-semibold">Fee follow-up (separate):</span>
                <span className="font-bold text-white">{countLabel(kpis.fee_follow_up_students || 0, 'student')}</span>
              </div>
            </div>
          </div>

          <Link
            to="/at-risk"
            className={buttonClass('primary', 'mt-6 w-full')}
          >
            <span>See students and reasons</span>
            <ArrowUpRight className="w-4 h-4" />
          </Link>
        </div>
      </div>
    </div>
  );
}
