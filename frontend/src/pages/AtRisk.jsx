import React, { useEffect, useState } from 'react';
import { AlertTriangle, ChevronRight, GraduationCap, Info, Receipt, Sliders, Users } from 'lucide-react';
import { api } from '../api/client';
import RiskDetailDialog from '../components/RiskDetailDialog';
import RiskSimulator from '../components/RiskSimulator';
import Button from '../components/ui/Button';
import { SearchInput } from '../components/ui/Field';
import { Card, PageHeader } from '../components/ui/Page';
import { EmptyState, ErrorNotice, ErrorState, LoadingState } from '../components/ui/States';
import { apiErrorMessage } from '../lib/errors';
import {
  MODEL_NOTE,
  NOT_ENOUGH_DATA,
  RISK_BANDS,
  bandCounts,
  bandLabel,
  bandStyle,
  feeFollowUpText,
  scoreText,
  studentsInBand,
} from '../lib/risk';

function StudentCard({ student, opening, onOpen }) {
  const style = bandStyle(student.risk_category);
  const feeText = feeFollowUpText(student.fee_follow_up);
  const { metrics } = student;
  const hasScore = student.risk_category !== NOT_ENOUGH_DATA;

  return (
    <div className={`bg-white rounded-2xl p-5 border ${style.card}`}>
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-base font-bold text-slate-900">{student.name}</h3>
            <span className="font-mono text-xs font-bold text-blue-700">#{student.roll_number}</span>
            <span className="text-xs px-2 py-0.5 rounded-md bg-slate-100 font-medium text-slate-700">{student.grade} - {student.section}</span>
          </div>
          <div className="flex flex-wrap items-center gap-2 mt-2">
            {metrics.avg_marks_pct !== null && (
              <span className="text-xs bg-slate-100 text-slate-700 px-2 py-0.5 rounded-md flex items-center gap-1 font-medium">
                <GraduationCap className="w-3 h-3 text-slate-500" />
                <span>Average <b>{metrics.avg_marks_pct}%</b> in {metrics.subjects_counted} subject{metrics.subjects_counted === 1 ? '' : 's'}</span>
              </span>
            )}
            {hasScore && (
              <span className={`text-xs px-2 py-0.5 rounded-md flex items-center gap-1 font-medium ${metrics.failing_subjects > 0 ? 'bg-rose-100 text-rose-800' : 'bg-slate-100 text-slate-700'}`}>
                <AlertTriangle className="w-3 h-3" />
                <span>Failed <b>{metrics.failing_subjects}</b></span>
              </span>
            )}
            {feeText && (
              <span className="text-xs px-2 py-0.5 rounded-md flex items-center gap-1 font-medium bg-amber-50 text-amber-900 border border-amber-200">
                <Receipt className="w-3 h-3" />
                <span>{feeText}</span>
              </span>
            )}
          </div>
        </div>

        <div className="flex md:flex-col items-center md:items-end justify-between gap-2 shrink-0">
          <div className="text-left md:text-right">
            <span className={`inline-block px-3 py-1 rounded-full text-xs font-bold border ${style.badge}`}>{bandLabel(student.risk_category)}</span>
            {hasScore && <p className="mt-1 text-xs text-slate-600">{scoreText(student.risk_score)}</p>}
          </div>
          <button onClick={onOpen} disabled={opening} className="inline-flex min-h-11 items-center gap-1 rounded-xl px-2 text-sm font-semibold text-brand-700 hover:bg-brand-50 disabled:opacity-50">
            <span>{opening ? 'Opening…' : 'Why and what next'}</span>
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
}

export default function AtRisk() {
  const [students, setStudents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [band, setBand] = useState('all');
  const [search, setSearch] = useState('');
  const [detail, setDetail] = useState(null);
  const [openingId, setOpeningId] = useState(null);
  const [detailError, setDetailError] = useState('');
  const [simulatorOpen, setSimulatorOpen] = useState(false);

  const fetchStudents = async () => {
    try {
      setLoading(true);
      setLoadError('');
      const res = await api.getAtRiskStudents();
      setStudents(res.data);
    } catch (err) {
      setLoadError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchStudents(); }, []);

  const openDetail = async (id) => {
    try {
      setOpeningId(id);
      setDetailError('');
      const res = await api.getStudentRiskDetail(id);
      setDetail(res.data);
    } catch (err) {
      setDetailError(apiErrorMessage(err));
    } finally {
      setOpeningId(null);
    }
  };

  const counts = bandCounts(students);
  const query = search.trim().toLowerCase();
  const shown = studentsInBand(students, band).filter((student) => (
    !query
    || student.name.toLowerCase().includes(query)
    || student.roll_number.toLowerCase().includes(query)
    || student.grade.toLowerCase().includes(query)
  ));

  return (
    <div className="space-y-6">
      <PageHeader
        title="Academic Early Warning"
        subtitle="An estimate of which students may need academic support, from exam marks only. Fees never affect it."
        actions={<Button variant="secondary" onClick={() => setSimulatorOpen(true)}><Sliders className="h-4 w-4" aria-hidden="true" /><span>Try the model</span></Button>}
      />

      <div className="flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 p-3.5 text-sm text-amber-900" role="note">
        <Info className="w-4 h-4 shrink-0 mt-0.5" />
        <p className="font-semibold">{MODEL_NOTE}</p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
        {RISK_BANDS.map(({ key, label, detail: bandDetail }) => (
          <button
            key={key}
            onClick={() => setBand(key)}
            aria-pressed={band === key}
            className={`p-4 rounded-2xl border text-left transition-colors ${band === key ? 'border-navy-800 bg-navy-800 text-white' : 'border-slate-200 bg-white text-slate-800 hover:bg-slate-50'}`}
          >
            <p className={`text-xs font-semibold ${band === key ? 'text-slate-200' : 'text-slate-600'}`}>{label}</p>
            <p className="text-2xl font-bold mt-1">{loading || loadError ? '–' : counts[key]}</p>
            <p className={`mt-0.5 text-xs ${band === key ? 'text-slate-200' : 'text-slate-600'}`}>{bandDetail}</p>
          </button>
        ))}
      </div>

      <Card className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
        <SearchInput label="Search by name, roll number, or grade" value={search} onChange={(event) => setSearch(event.target.value)} className="w-full max-w-md" />
        <p className="text-sm text-slate-600">Showing <b>{shown.length}</b> of {students.length}</p>
      </Card>

      <ErrorNotice>{detailError}</ErrorNotice>

      <div className="space-y-3">
        {loading && <Card><LoadingState label="Loading estimates…" /></Card>}
        {!loading && loadError && <Card><ErrorState message={loadError} onRetry={fetchStudents} /></Card>}
        {!loading && !loadError && shown.length === 0 && <Card><EmptyState icon={Users} title="No students match this view" message="Try a different band or search." /></Card>}
        {!loading && !loadError && shown.map((student) => (
          <StudentCard key={student.id} student={student} opening={openingId === student.id} onOpen={() => openDetail(student.id)} />
        ))}
      </div>

      {simulatorOpen && <RiskSimulator onClose={() => setSimulatorOpen(false)} />}
      {detail && <RiskDetailDialog detail={detail} onClose={() => setDetail(null)} />}
    </div>
  );
}
