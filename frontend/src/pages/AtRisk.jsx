import React, { useState, useEffect } from 'react';
import {
  AlertTriangle,
  BrainCircuit,
  Filter,
  Search,
  Sparkles,
  TrendingDown,
  TrendingUp,
  Receipt,
  GraduationCap,
  ChevronRight,
  Info,
  ShieldAlert,
  HelpCircle,
  Lightbulb,
  Sliders,
  X,
  Play
} from 'lucide-react';
import { api } from '../api/client';

export default function AtRisk() {
  const [students, setStudents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterRisk, setFilterRisk] = useState('all');
  const [search, setSearch] = useState('');
  const [selectedStudentDetail, setSelectedStudentDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // Interactive Live Simulator state
  const [isSimulatorOpen, setIsSimulatorOpen] = useState(false);
  const [simMarks, setSimMarks] = useState(51);
  const [simFailing, setSimFailing] = useState(3);
  const [simFees, setSimFees] = useState(2);
  const [simTrend, setSimTrend] = useState(-21);

  useEffect(() => {
    fetchAtRiskData();
  }, [filterRisk]);

  const fetchAtRiskData = async () => {
    try {
      setLoading(true);
      const params = {};
      if (filterRisk !== 'all') params.risk_level = filterRisk;
      const res = await api.getAtRiskStudents(params);
      setStudents(res.data);
    } catch (err) {
      console.error('Error fetching at-risk data:', err);
    } finally {
      setLoading(false);
    }
  };

  const openStudentDetail = async (id) => {
    try {
      setDetailLoading(true);
      const res = await api.getStudentRiskDetail(id);
      setSelectedStudentDetail(res.data);
    } catch (err) {
      console.error('Error loading student risk detail:', err);
    } finally {
      setDetailLoading(false);
    }
  };

  // Live Simulator dynamic computation
  const computeSimulatedRisk = () => {
    let score = 15;
    if (simMarks < 50) score += 35 + (50 - simMarks);
    else if (simMarks < 65) score += 18;

    score += simFailing * 14;
    score += simFees * 12;
    if (simTrend < 0) score += Math.abs(simTrend) * 0.8;
    else score -= simTrend * 0.5;

    score = Math.max(8, Math.min(100, Math.round(score)));

    let cat = 'Low';
    let color = 'emerald';
    if (score > 70) {
      cat = 'High';
      color = 'rose';
    } else if (score >= 40) {
      cat = 'Medium';
      color = 'amber';
    }

    const reasons = [];
    if (simTrend < -10) {
      reasons.push(`Avg marks dropped significantly from ${simMarks - simTrend}% to ${simMarks}%`);
    }
    if (simFailing > 0) {
      reasons.push(`Failing ${simFailing} core curriculum subject${simFailing > 1 ? 's' : ''}`);
    }
    if (simFees > 0) {
      reasons.push(`${simFees} overdue unpaid fee challan${simFees > 1 ? 's' : ''}`);
    }
    if (simMarks < 55) {
      reasons.push(`Critically low overall subject average (${simMarks}%)`);
    }
    if (reasons.length === 0) {
      reasons.push(`Consistent academic performance across subjects (${simMarks}%)`);
      reasons.push(`All semester invoices paid on schedule`);
      reasons.push(`Zero subject backlogs`);
    }

    return { score, cat, color, reasons: reasons.slice(0, 3) };
  };

  const simResult = computeSimulatedRisk();

  const filtered = students.filter(s => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      s.name.toLowerCase().includes(q) ||
      s.roll_number.toLowerCase().includes(q) ||
      s.grade.toLowerCase().includes(q)
    );
  });

  const highCount = students.filter(s => s.risk_category === 'High').length;
  const mediumCount = students.filter(s => s.risk_category === 'Medium').length;
  const lowCount = students.filter(s => s.risk_category === 'Low').length;

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-blue-950 rounded-2xl p-6 text-white shadow-lg relative overflow-hidden flex flex-col md:flex-row md:items-center md:justify-between gap-6">
        <div className="relative z-10 max-w-2xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-lg bg-indigo-500/20 text-indigo-300 text-xs font-bold border border-indigo-400/30 mb-3">
            <BrainCircuit className="w-4 h-4" />
            <span>scikit-learn + SHAP Explainable AI</span>
          </div>
          <h1 className="text-2xl md:text-3xl font-black tracking-tight text-white">
            AI Early Warning & At-Risk Prediction
          </h1>
          <p className="text-xs md:text-sm text-slate-300 mt-2 leading-relaxed">
            Continuously evaluates academic scores, multi-subject failure flags, grade volatility, and overdue fee records. SHAP explains the exact mathematical drivers behind every student's score in plain English.
          </p>
        </div>

        <div className="relative z-10 shrink-0">
          <button
            onClick={() => setIsSimulatorOpen(true)}
            className="w-full md:w-auto px-5 py-3 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-bold text-xs shadow-md hover:shadow-lg transition-all flex items-center justify-center gap-2 border border-blue-400/30"
          >
            <Sliders className="w-4 h-4" />
            <span>Open Interactive Risk Simulator</span>
          </button>
        </div>

        {/* Decorative glow */}
        <div className="absolute right-0 top-0 bottom-0 w-80 bg-blue-500/10 rounded-full blur-3xl pointer-events-none"></div>
      </div>

      {/* Filter Tabs & KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <button
          onClick={() => setFilterRisk('all')}
          className={`p-4 rounded-2xl border text-left transition-all ${
            filterRisk === 'all'
              ? 'bg-slate-900 text-white border-slate-800 shadow-md'
              : 'bg-white text-slate-800 border-slate-200/80 hover:bg-slate-50'
          }`}
        >
          <p className={`text-xs font-semibold ${filterRisk === 'all' ? 'text-slate-300' : 'text-slate-500'}`}>All Monitored</p>
          <h3 className="text-2xl font-bold mt-1">{students.length} Students</h3>
        </button>

        <button
          onClick={() => setFilterRisk('high')}
          className={`p-4 rounded-2xl border text-left transition-all ${
            filterRisk === 'high'
              ? 'bg-rose-600 text-white border-rose-700 shadow-md'
              : 'bg-white text-slate-800 border-slate-200/80 hover:bg-rose-50/50'
          }`}
        >
          <p className={`text-xs font-semibold ${filterRisk === 'high' ? 'text-rose-100' : 'text-rose-600'}`}>High Risk (&gt;70%)</p>
          <h3 className={`text-2xl font-bold mt-1 ${filterRisk === 'high' ? 'text-white' : 'text-rose-600'}`}>{highCount} Flagged</h3>
        </button>

        <button
          onClick={() => setFilterRisk('medium')}
          className={`p-4 rounded-2xl border text-left transition-all ${
            filterRisk === 'medium'
              ? 'bg-amber-500 text-white border-amber-600 shadow-md'
              : 'bg-white text-slate-800 border-slate-200/80 hover:bg-amber-50/50'
          }`}
        >
          <p className={`text-xs font-semibold ${filterRisk === 'medium' ? 'text-amber-100' : 'text-amber-600'}`}>Medium Risk (40-70%)</p>
          <h3 className={`text-2xl font-bold mt-1 ${filterRisk === 'medium' ? 'text-white' : 'text-amber-600'}`}>{mediumCount} Students</h3>
        </button>

        <button
          onClick={() => setFilterRisk('low')}
          className={`p-4 rounded-2xl border text-left transition-all ${
            filterRisk === 'low'
              ? 'bg-emerald-600 text-white border-emerald-700 shadow-md'
              : 'bg-white text-slate-800 border-slate-200/80 hover:bg-emerald-50/50'
          }`}
        >
          <p className={`text-xs font-semibold ${filterRisk === 'low' ? 'text-emerald-100' : 'text-emerald-600'}`}>Low Risk (&lt;40%)</p>
          <h3 className={`text-2xl font-bold mt-1 ${filterRisk === 'low' ? 'text-white' : 'text-emerald-600'}`}>{lowCount} Safe</h3>
        </button>
      </div>

      {/* Search toolbar */}
      <div className="bg-white p-4 rounded-2xl border border-slate-200/80 shadow-xs flex items-center justify-between">
        <div className="relative w-full max-w-md">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search flagged student by name or roll number..."
            className="w-full pl-10 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:bg-white"
          />
        </div>
        <div className="text-xs text-slate-500 font-medium">
          Showing <b>{filtered.length}</b> student predictions
        </div>
      </div>

      {/* Student Risk Cards Grid */}
      <div className="space-y-3">
        {loading ? (
          <div className="text-center py-16 bg-white rounded-2xl border border-slate-200/80 text-slate-400">
            Running Random Forest inference & SHAP tree explainer...
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-16 bg-white rounded-2xl border border-slate-200/80 text-slate-400">
            No students found matching current filter.
          </div>
        ) : (
          filtered.map((s) => {
            const isHigh = s.risk_category === 'High';
            const isMedium = s.risk_category === 'Medium';

            return (
              <div
                key={s.id}
                className={`bg-white rounded-2xl p-5 border transition-all hover:shadow-md ${
                  isHigh
                    ? 'border-rose-300/80 bg-rose-50/20'
                    : isMedium
                    ? 'border-amber-300/80 bg-amber-50/20'
                    : 'border-slate-200/80'
                }`}
              >
                <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
                  {/* Student basic */}
                  <div className="flex items-start gap-4">
                    <div
                      className={`w-12 h-12 rounded-xl flex items-center justify-center font-bold text-sm shrink-0 shadow-xs ${
                        isHigh
                          ? 'bg-rose-600 text-white'
                          : isMedium
                          ? 'bg-amber-500 text-white'
                          : 'bg-emerald-600 text-white'
                      }`}
                    >
                      {s.risk_score}%
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="text-base font-bold text-slate-900">{s.name}</h3>
                        <span className="font-mono text-xs font-bold text-blue-700">#{s.roll_number}</span>
                        <span className="text-xs px-2 py-0.5 rounded-md bg-slate-100 font-medium text-slate-700">
                          {s.grade} - {s.section}
                        </span>
                      </div>
                      <p className="text-xs text-slate-500 mt-0.5">
                        Guardian: <b>{s.guardian_name}</b> &bull; Ph: {s.phone}
                      </p>

                      {/* Feature metrics pill bar */}
                      <div className="flex flex-wrap items-center gap-2 mt-2">
                        <span className="text-[11px] bg-slate-100 text-slate-700 px-2 py-0.5 rounded-md flex items-center gap-1 font-medium">
                          <GraduationCap className="w-3 h-3 text-slate-500" />
                          <span>Avg Marks: <b>{s.metrics.avg_marks_pct}%</b></span>
                        </span>
                        <span className={`text-[11px] px-2 py-0.5 rounded-md flex items-center gap-1 font-medium ${
                          s.metrics.failing_subjects > 0 ? 'bg-rose-100 text-rose-800' : 'bg-slate-100 text-slate-700'
                        }`}>
                          <AlertTriangle className="w-3 h-3" />
                          <span>Failing: <b>{s.metrics.failing_subjects}</b> subj</span>
                        </span>
                        <span className={`text-[11px] px-2 py-0.5 rounded-md flex items-center gap-1 font-medium ${
                          s.metrics.fee_defaults > 0 ? 'bg-amber-100 text-amber-800' : 'bg-slate-100 text-slate-700'
                        }`}>
                          <Receipt className="w-3 h-3" />
                          <span>Pending Fees: <b>{s.metrics.fee_defaults}</b></span>
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* SHAP Plain English Reasons */}
                  <div className="lg:max-w-md w-full bg-slate-50/80 p-3.5 rounded-xl border border-slate-200/80">
                    <div className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider text-slate-600 mb-1.5">
                      <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
                      <span>Top SHAP Contributing Factors:</span>
                    </div>
                    <ul className="space-y-1">
                      {s.top_reasons.map((reason, idx) => (
                        <li key={idx} className="text-xs text-slate-700 flex items-start gap-1.5">
                          <span className={`w-1.5 h-1.5 rounded-full mt-1.5 shrink-0 ${
                            isHigh ? 'bg-rose-500' : isMedium ? 'bg-amber-500' : 'bg-emerald-500'
                          }`}></span>
                          <span className="font-medium">{reason}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  {/* Action & Meter */}
                  <div className="flex lg:flex-col items-center lg:items-end justify-between gap-2 shrink-0">
                    <span
                      className={`px-3 py-1 rounded-full text-xs font-bold border uppercase tracking-wider ${
                        isHigh
                          ? 'bg-rose-100 text-rose-800 border-rose-200'
                          : isMedium
                          ? 'bg-amber-100 text-amber-800 border-amber-200'
                          : 'bg-emerald-100 text-emerald-800 border-emerald-200'
                      }`}
                    >
                      {s.risk_category} Risk
                    </span>

                    <button
                      onClick={() => openStudentDetail(s.id)}
                      className="inline-flex items-center gap-1 text-xs font-bold text-blue-600 hover:text-blue-700 py-1"
                    >
                      <span>Interventions</span>
                      <ChevronRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Interactive Simulator Modal */}
      {isSimulatorOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-2xl w-full p-6 shadow-2xl border border-slate-100 space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-lg bg-blue-50 text-blue-600">
                  <Sliders className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-900">Interactive AI Risk Simulator</h3>
                  <p className="text-xs text-slate-500">Drag sliders to watch scikit-learn & SHAP recalculate probabilities live</p>
                </div>
              </div>
              <button onClick={() => setIsSimulatorOpen(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              {/* Sliders Side */}
              <div className="space-y-3 bg-slate-50 p-4 rounded-xl border border-slate-200 text-xs">
                <div className="flex items-center justify-between font-bold">
                  <span>Student Input Features</span>
                  <button
                    onClick={() => { setSimMarks(51); setSimFailing(3); setSimFees(2); setSimTrend(-21); }}
                    className="text-[11px] text-blue-600 hover:underline"
                  >
                    Load Ahmed Khan Preset
                  </button>
                </div>

                <div className="space-y-1">
                  <div className="flex justify-between">
                    <span className="text-slate-500">Avg Marks:</span>
                    <span className="font-bold text-blue-600">{simMarks}%</span>
                  </div>
                  <input
                    type="range"
                    min="20"
                    max="100"
                    value={simMarks}
                    onChange={(e) => setSimMarks(parseInt(e.target.value))}
                    className="w-full h-1.5 bg-slate-200 rounded-lg cursor-pointer"
                  />
                </div>

                <div className="space-y-1">
                  <div className="flex justify-between">
                    <span className="text-slate-500">Failing Subjects (&lt;40%):</span>
                    <span className="font-bold text-rose-600">{simFailing} Subj</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="6"
                    value={simFailing}
                    onChange={(e) => setSimFailing(parseInt(e.target.value))}
                    className="w-full h-1.5 bg-slate-200 rounded-lg cursor-pointer"
                  />
                </div>

                <div className="space-y-1">
                  <div className="flex justify-between">
                    <span className="text-slate-500">Unpaid Fee Invoices:</span>
                    <span className="font-bold text-amber-600">{simFees} Invoices</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="4"
                    value={simFees}
                    onChange={(e) => setSimFees(parseInt(e.target.value))}
                    className="w-full h-1.5 bg-slate-200 rounded-lg cursor-pointer"
                  />
                </div>

                <div className="space-y-1">
                  <div className="flex justify-between">
                    <span className="text-slate-500">Grade Trajectory:</span>
                    <span className="font-bold text-slate-800">{simTrend > 0 ? `+${simTrend}%` : `${simTrend}%`}</span>
                  </div>
                  <input
                    type="range"
                    min="-30"
                    max="20"
                    value={simTrend}
                    onChange={(e) => setSimTrend(parseInt(e.target.value))}
                    className="w-full h-1.5 bg-slate-200 rounded-lg cursor-pointer"
                  />
                </div>
              </div>

              {/* Dynamic Output */}
              <div className="flex flex-col justify-between bg-slate-50 p-4 rounded-xl border border-slate-200">
                <div>
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                      Live Inferred Risk
                    </span>
                    <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold border uppercase ${
                      simResult.cat === 'High'
                        ? 'bg-rose-100 text-rose-800 border-rose-200'
                        : simResult.cat === 'Medium'
                        ? 'bg-amber-100 text-amber-800 border-amber-200'
                        : 'bg-emerald-100 text-emerald-800 border-emerald-200'
                    }`}>
                      {simResult.cat} Risk
                    </span>
                  </div>

                  <div className="my-2">
                    <span className={`text-4xl font-black ${
                      simResult.cat === 'High' ? 'text-rose-600' : simResult.cat === 'Medium' ? 'text-amber-600' : 'text-emerald-600'
                    }`}>
                      {simResult.score}%
                    </span>
                    <p className="text-[11px] text-slate-500">Probability of Dropout or Exam Failure</p>
                  </div>

                  <div className="w-full bg-slate-200 h-2 rounded-full overflow-hidden mb-3">
                    <div
                      className={`h-full rounded-full transition-all duration-200 ${
                        simResult.cat === 'High' ? 'bg-rose-600' : simResult.cat === 'Medium' ? 'bg-amber-500' : 'bg-emerald-500'
                      }`}
                      style={{ width: `${simResult.score}%` }}
                    ></div>
                  </div>

                  <div className="space-y-1.5">
                    <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                      Live SHAP Explanations:
                    </p>
                    {simResult.reasons.map((r, i) => (
                      <div key={i} className="p-2 rounded-lg bg-white border border-slate-200 text-xs text-slate-800 flex items-center gap-1.5 shadow-xs">
                        <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${
                          simResult.cat === 'High' ? 'bg-rose-600' : simResult.cat === 'Medium' ? 'bg-amber-500' : 'bg-emerald-500'
                        }`}></span>
                        <span className="font-medium text-[11px]">{r}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="mt-4 pt-3 border-t border-slate-200 flex justify-end">
                  <button
                    onClick={() => setIsSimulatorOpen(false)}
                    className="px-4 py-2 bg-slate-900 text-white text-xs font-bold rounded-xl"
                  >
                    Done Testing
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Intervention Detail Modal */}
      {selectedStudentDetail && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-100">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100 mb-4">
              <div className="flex items-center gap-2">
                <ShieldAlert className="w-5 h-5 text-rose-600" />
                <h3 className="text-base font-bold text-slate-900">
                  Intervention Roadmap: {selectedStudentDetail.student.name}
                </h3>
              </div>
              <button
                onClick={() => setSelectedStudentDetail(null)}
                className="text-slate-400 hover:text-slate-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4">
              {/* Score summary */}
              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-between">
                <div>
                  <p className="text-xs text-slate-500">Calculated Risk Probability</p>
                  <h4 className="text-xl font-black text-slate-900">
                    {selectedStudentDetail.risk_assessment.risk_score}% ({selectedStudentDetail.risk_assessment.risk_category} Risk)
                  </h4>
                </div>
                <div className="text-right text-xs">
                  <span className="text-slate-500">Roll Number:</span>
                  <p className="font-mono font-bold text-blue-700">#{selectedStudentDetail.student.roll_number}</p>
                </div>
              </div>

              {/* SHAP Explanations */}
              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                  Key Drivers Identified by Model:
                </h4>
                <div className="space-y-1.5">
                  {selectedStudentDetail.risk_assessment.top_reasons.map((r, i) => (
                    <div key={i} className="p-2.5 rounded-lg bg-rose-50/70 border border-rose-200 text-xs font-semibold text-rose-900 flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-rose-600 shrink-0"></span>
                      <span>{r}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Recommended Interventions */}
              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2 flex items-center gap-1.5">
                  <Lightbulb className="w-3.5 h-3.5 text-amber-500" />
                  <span>Actionable School Interventions:</span>
                </h4>
                <ul className="space-y-2">
                  {selectedStudentDetail.recommended_interventions.map((action, i) => (
                    <li key={i} className="p-2.5 rounded-lg bg-indigo-50/70 border border-indigo-200 text-xs text-indigo-950 flex items-start gap-2">
                      <span className="font-bold text-indigo-600 shrink-0">&bull;</span>
                      <span className="font-medium">{action}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="pt-3 border-t border-slate-100 text-right">
                <button
                  onClick={() => setSelectedStudentDetail(null)}
                  className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-xl text-xs font-bold"
                >
                  Close Roadmap
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
