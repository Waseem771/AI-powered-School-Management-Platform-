import React, { useEffect, useState } from 'react';
import { AlertTriangle, ChevronRight, GraduationCap, Info, Receipt, RefreshCw, Search, Sliders } from 'lucide-react';
import { api } from '../api/client';
import RiskDetailDialog from '../components/RiskDetailDialog';
import RiskSimulator from '../components/RiskSimulator';
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
              <span className="text-[11px] bg-slate-100 text-slate-700 px-2 py-0.5 rounded-md flex items-center gap-1 font-medium">
                <GraduationCap className="w-3 h-3 text-slate-500" />
                <span>Average <b>{metrics.avg_marks_pct}%</b> in {metrics.subjects_counted} subject{metrics.subjects_counted === 1 ? '' : 's'}</span>
              </span>
            )}
            {hasScore && (
              <span className={`text-[11px] px-2 py-0.5 rounded-md flex items-center gap-1 font-medium ${metrics.failing_subjects > 0 ? 'bg-rose-100 text-rose-800' : 'bg-slate-100 text-slate-700'}`}>
                <AlertTriangle className="w-3 h-3" />
                <span>Failed <b>{metrics.failing_subjects}</b></span>
              </span>
            )}
            {feeText && (
              <span className="text-[11px] px-2 py-0.5 rounded-md flex items-center gap-1 font-medium bg-amber-50 text-amber-900 border border-amber-200">
                <Receipt className="w-3 h-3" />
                <span>{feeText}</span>
              </span>
            )}
          </div>
        </div>

        <div className="flex md:flex-col items-center md:items-end justify-between gap-2 shrink-0">
          <div className="text-left md:text-right">
            <span className={`inline-block px-3 py-1 rounded-full text-xs font-bold border ${style.badge}`}>{bandLabel(student.risk_category)}</span>
            {hasScore && <p className="text-[11px] text-slate-500 mt-1">{scoreText(student.risk_score)}</p>}
          </div>
          <button onClick={onOpen} disabled={opening} className="min-h-11 inline-flex items-center gap-1 text-xs font-bold text-blue-600 hover:text-blue-700 disabled:opacity-50">
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
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-blue-950 rounded-2xl p-6 text-white shadow-lg flex flex-col md:flex-row md:items-center md:justify-between gap-6">
        <div className="max-w-2xl">
          <h1 className="text-2xl md:text-3xl font-black tracking-tight text-white">Academic Early Warning</h1>
          <p className="text-xs md:text-sm text-slate-300 mt-2 leading-relaxed">
            An estimate of which students may need academic support, from their latest exam marks and, when both exist, the change from midterm to final. Fees never affect it. Each student's reasons open with "Why and what next".
          </p>
        </div>
        <button onClick={() => setSimulatorOpen(true)} className="min-h-11 shrink-0 px-5 py-3 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs flex items-center justify-center gap-2">
          <Sliders className="w-4 h-4" />
          <span>Try the model</span>
        </button>
      </div>

      <div className="flex items-start gap-2 p-3.5 rounded-xl border border-amber-200 bg-amber-50 text-xs text-amber-900" role="note">
        <Info className="w-4 h-4 shrink-0 mt-0.5" />
        <p className="font-semibold">{MODEL_NOTE}</p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
        {RISK_BANDS.map(({ key, label, detail: bandDetail }) => (
          <button
            key={key}
            onClick={() => setBand(key)}
            aria-pressed={band === key}
            className={`p-4 rounded-2xl border text-left transition-colors ${band === key ? 'bg-slate-900 text-white border-slate-800' : 'bg-white text-slate-800 border-slate-200/80 hover:bg-slate-50'}`}
          >
            <p className={`text-xs font-semibold ${band === key ? 'text-slate-200' : 'text-slate-600'}`}>{label}</p>
            <p className="text-2xl font-bold mt-1">{loading || loadError ? '–' : counts[key]}</p>
            <p className={`text-[11px] mt-0.5 ${band === key ? 'text-slate-300' : 'text-slate-500'}`}>{bandDetail}</p>
          </button>
        ))}
      </div>

      <div className="bg-white p-4 rounded-2xl border border-slate-200/80 shadow-xs flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="relative w-full max-w-md">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search by name, roll number, or grade"
            className="w-full pl-10 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:bg-white"
          />
        </div>
        <p className="text-xs text-slate-500 font-medium">Showing <b>{shown.length}</b> of {students.length}</p>
      </div>

      {detailError && <p role="alert" className="text-xs text-rose-700 bg-rose-50 border border-rose-200 rounded-xl p-3">{detailError}</p>}

      <div className="space-y-3">
        {loading && <div role="status" className="text-center py-16 bg-white rounded-2xl border border-slate-200/80 text-slate-500 text-sm">Loading estimates…</div>}
        {!loading && loadError && (
          <div role="alert" className="text-center py-12 bg-white rounded-2xl border border-rose-200 space-y-3">
            <p className="text-sm text-rose-700">{loadError}</p>
            <button onClick={fetchStudents} className="min-h-11 inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-slate-900 text-white text-xs font-bold">
              <RefreshCw className="w-3.5 h-3.5" /> <span>Try again</span>
            </button>
          </div>
        )}
        {!loading && !loadError && shown.length === 0 && (
          <div className="text-center py-16 bg-white rounded-2xl border border-slate-200/80 text-slate-500 text-sm">No students match this view.</div>
        )}
        {!loading && !loadError && shown.map((student) => (
          <StudentCard key={student.id} student={student} opening={openingId === student.id} onOpen={() => openDetail(student.id)} />
        ))}
      </div>

      {simulatorOpen && <RiskSimulator onClose={() => setSimulatorOpen(false)} />}
      {detail && <RiskDetailDialog detail={detail} onClose={() => setDetail(null)} />}
    </div>
  );
}
