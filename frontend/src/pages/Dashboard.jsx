import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Users,
  CreditCard,
  AlertOctagon,
  TrendingUp,
  UserPlus,
  FileText,
  Bot,
  ArrowUpRight,
  Sparkles,
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
import StatCard from '../components/StatCard';

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
      console.error('Error fetching dashboard stats:', err);
      setError('Dashboard data is unavailable. Confirm that the backend is running, then try again.');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
          <p className="text-sm text-slate-500 font-medium">Loading Al-Noor Academy analytics...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <section className="mx-auto flex min-h-[60vh] max-w-lg items-center" aria-labelledby="dashboard-unavailable-title">
        <div className="w-full rounded-2xl border border-amber-200 bg-amber-50 p-6 shadow-sm">
          <h1 id="dashboard-unavailable-title" className="text-lg font-bold text-slate-900">Dashboard temporarily unavailable</h1>
          <p className="mt-2 text-sm leading-6 text-slate-700">{error}</p>
          <button onClick={fetchDashboardStats} className="mt-5 min-h-11 rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800">
            Try again
          </button>
        </div>
      </section>
    );
  }

  const kpis = stats?.kpis || {};
  const feeSummary = stats?.fee_summary || [];
  const gradeData = stats?.grade_distribution || [];
  const riskBreakdown = stats?.risk_breakdown || [];
  const subjectAverages = stats?.subject_performance || [];

  return (
    <div className="space-y-7">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Executive Dashboard</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Real-time administrative metrics, AI early warnings, and fee tracking.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link
            to="/students"
            className="inline-flex items-center gap-2 px-3.5 py-2 bg-white border border-slate-200 rounded-xl text-xs font-semibold text-slate-700 hover:bg-slate-50 shadow-xs transition-colors"
          >
            <UserPlus className="w-4 h-4 text-blue-600" />
            <span>Add Student</span>
          </Link>
          <Link
            to="/chatbot"
            className="inline-flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-xl text-xs font-semibold text-white shadow-sm hover:from-blue-700 hover:to-indigo-700 transition-all"
          >
            <Bot className="w-4 h-4" />
            <span>AI Policy Bot</span>
          </Link>
        </div>
      </div>

      {/* Top 4 KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Enrollment"
          value={`${kpis.total_students ?? 0} Students`}
          subtitle="Grades 6 to 10 active"
          icon={Users}
          color="blue"
          trend="100% Active"
        />
        <StatCard
          title="Fees Collected"
          value={`Rs. ${(kpis.total_collected || 0).toLocaleString()}`}
          subtitle={`${kpis.collection_rate || 0}% recovery rate`}
          icon={CheckCircle2}
          color="green"
        />
        <StatCard
          title="Pending Receivables"
          value={`Rs. ${(kpis.total_pending || 0).toLocaleString()}`}
          subtitle="Overdue fee challans"
          icon={Clock}
          color="amber"
        />
        <StatCard
          title="At-Risk Students"
          value={`${kpis.at_risk_students || 0} Flagged`}
          subtitle="Requires academic intervention"
          icon={AlertOctagon}
          color="red"
          trend="AI Monitored"
        />
      </div>

      {/* Analytics Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Grade Distribution Bar Chart */}
        <div className="lg:col-span-2 bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-base font-bold text-slate-800">Student Enrollment by Grade</h2>
              <p className="text-xs text-slate-500">Distribution of enrolled pupils across academic levels</p>
            </div>
            <span className="text-xs font-semibold px-2.5 py-1 bg-slate-100 text-slate-700 rounded-lg">
              5 Grades
            </span>
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
                <Bar dataKey="count" name="Students" fill="#3B82F6" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Fee Collection Donut Chart */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs flex flex-col justify-between">
          <div>
            <h2 className="text-base font-bold text-slate-800">Fee Recovery Ratio</h2>
            <p className="text-xs text-slate-500">Paid vs Pending invoices for active term</p>
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
                <span>Pending Receivables:</span>
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
              <h2 className="text-base font-bold text-slate-800">Curriculum Subject Averages</h2>
              <p className="text-xs text-slate-500">Average percentage achieved across all grades</p>
            </div>
            <span className="text-xs font-semibold px-2.5 py-1 bg-indigo-50 text-indigo-700 rounded-lg">
              Term Finals
            </span>
          </div>
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
                <Bar dataKey="average" name="Average %" fill="#6366F1" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* AI Early Warning Banner Card */}
        <div className="bg-gradient-to-br from-slate-900 to-indigo-950 p-6 rounded-2xl text-white shadow-md flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 mb-3">
              <span className="p-1.5 rounded-lg bg-indigo-500/30 text-indigo-300">
                <Sparkles className="w-4 h-4" />
              </span>
              <span className="text-xs font-bold uppercase tracking-wider text-indigo-300">
                Machine Learning Early Warning
              </span>
            </div>
            <h3 className="text-xl font-black text-white">Student At-Risk Radar</h3>
            <p className="text-xs text-slate-300 mt-2 leading-relaxed">
              Powered by <b>scikit-learn</b> Random Forest and <b>SHAP</b> explainability. Predicts dropout and academic failure probability with plain-English root causes.
            </p>

            <div className="mt-5 space-y-2">
              <div className="flex items-center justify-between text-xs bg-white/10 px-3 py-2 rounded-xl">
                <span className="text-rose-300 font-semibold">&bull; High Risk (&gt;70%):</span>
                <span className="font-bold text-white">{kpis.at_risk_students || 0} Students</span>
              </div>
              <div className="flex items-center justify-between text-xs bg-white/10 px-3 py-2 rounded-xl">
                <span className="text-amber-300 font-semibold">&bull; Medium Risk (40-70%):</span>
                <span className="font-bold text-white">{kpis.medium_risk_students || 0} Students</span>
              </div>
              <div className="flex items-center justify-between text-xs bg-white/10 px-3 py-2 rounded-xl">
                <span className="text-emerald-300 font-semibold">&bull; Low Risk (&lt;40%):</span>
                <span className="font-bold text-white">{kpis.low_risk_students || 0} Students</span>
              </div>
            </div>
          </div>

          <Link
            to="/at-risk"
            className="mt-6 w-full py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-bold flex items-center justify-center gap-1.5 transition-colors shadow-sm"
          >
            <span>Inspect AI Explanations</span>
            <ArrowUpRight className="w-4 h-4" />
          </Link>
        </div>
      </div>
    </div>
  );
}
