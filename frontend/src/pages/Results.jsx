import React, { useState, useEffect } from 'react';
import {
  GraduationCap,
  Download,
  Plus,
  Award,
  CheckCircle2,
  AlertCircle,
  FileCheck,
  Percent,
  X
} from 'lucide-react';
import { api } from '../api/client';

const SUBJECTS = ["English", "Urdu", "Mathematics", "Science", "Islamiat", "Pakistan Studies"];

export default function Results() {
  const [students, setStudents] = useState([]);
  const [selectedStudentId, setSelectedStudentId] = useState('');
  const [studentData, setStudentData] = useState(null);
  const [loading, setLoading] = useState(false);

  // Add / Edit Marks modal
  const [isEntryOpen, setIsEntryOpen] = useState(false);
  const [entryForm, setEntryForm] = useState({
    subject: 'Mathematics',
    marks_obtained: 85,
    total_marks: 100,
    exam_type: 'Final Term'
  });
  const [entryMsg, setEntryMsg] = useState('');

  useEffect(() => {
    fetchStudents();
  }, []);

  useEffect(() => {
    if (selectedStudentId) {
      fetchStudentResults(selectedStudentId);
    }
  }, [selectedStudentId]);

  const fetchStudents = async () => {
    try {
      const res = await api.getStudents();
      setStudents(res.data);
      if (res.data.length > 0) {
        // Find Ahmed Khan first if present for showcase
        const ahmed = res.data.find(s => s.roll_number === '045');
        const defaultId = ahmed ? ahmed.id : res.data[0].id;
        setSelectedStudentId(defaultId);
      }
    } catch (err) {
      console.error('Error loading students:', err);
    }
  };

  const fetchStudentResults = async (id) => {
    try {
      setLoading(true);
      const res = await api.getStudentResults(id);
      setStudentData(res.data);
    } catch (err) {
      console.error('Error fetching student results:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveMarks = async (e) => {
    e.preventDefault();
    setEntryMsg('');
    try {
      await api.enterMarks({
        student_id: parseInt(selectedStudentId),
        subject: entryForm.subject,
        marks_obtained: parseFloat(entryForm.marks_obtained),
        total_marks: parseFloat(entryForm.total_marks),
        exam_type: entryForm.exam_type
      });
      setIsEntryOpen(false);
      fetchStudentResults(selectedStudentId);
    } catch (err) {
      setEntryMsg(err.response?.data?.detail || 'Failed to record marks.');
    }
  };

  const results = studentData?.results || [];
  const summary = studentData?.summary || {};
  const currentStudent = studentData?.student || {};

  const getGradeColor = (grade) => {
    switch (grade) {
      case 'A+':
      case 'A':
        return 'bg-emerald-100 text-emerald-800 border-emerald-200';
      case 'B':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'C':
        return 'bg-amber-100 text-amber-800 border-amber-200';
      case 'D':
        return 'bg-orange-100 text-orange-800 border-orange-200';
      default:
        return 'bg-rose-100 text-rose-800 border-rose-200';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Examination & Report Cards</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Grade entry, academic progress tracking, and official ReportLab Report Card PDF issuance.
          </p>
        </div>

        {selectedStudentId && (
          <div className="flex items-center gap-3">
            <button
              onClick={() => setIsEntryOpen(true)}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-white border border-slate-200 rounded-xl text-xs font-semibold text-slate-700 hover:bg-slate-50 shadow-xs transition-colors"
            >
              <Plus className="w-4 h-4 text-blue-600" />
              <span>Update / Enter Mark</span>
            </button>
            <a
              href={api.getReportCardPdfUrl(selectedStudentId)}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-bold shadow-sm transition-all"
            >
              <Download className="w-4 h-4" />
              <span>Download Report Card PDF</span>
            </a>
          </div>
        )}
      </div>

      {/* Student Selector Card */}
      <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="w-full sm:w-auto">
          <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
            Select Student Record
          </label>
          <select
            value={selectedStudentId}
            onChange={(e) => setSelectedStudentId(e.target.value)}
            className="w-full sm:w-80 px-3.5 py-2.5 text-xs bg-slate-50 border border-slate-200 rounded-xl font-medium focus:outline-none focus:ring-2 focus:ring-blue-600"
          >
            {students.map(s => (
              <option key={s.id} value={s.id}>
                #{s.roll_number} - {s.name} ({s.grade}-{s.section})
              </option>
            ))}
          </select>
        </div>

        {currentStudent.name && (
          <div className="flex items-center gap-4 bg-slate-50 px-4 py-2.5 rounded-xl border border-slate-200 w-full sm:w-auto justify-between sm:justify-start">
            <div>
              <span className="text-[10px] uppercase font-bold text-slate-400">Class</span>
              <p className="text-xs font-bold text-slate-800">{currentStudent.grade} - {currentStudent.section}</p>
            </div>
            <div className="h-6 w-px bg-slate-200"></div>
            <div>
              <span className="text-[10px] uppercase font-bold text-slate-400">Guardian</span>
              <p className="text-xs font-bold text-slate-800">{currentStudent.guardian_name}</p>
            </div>
            <div className="h-6 w-px bg-slate-200"></div>
            <div>
              <span className="text-[10px] uppercase font-bold text-slate-400">Roll No</span>
              <p className="text-xs font-mono font-bold text-blue-700">#{currentStudent.roll_number}</p>
            </div>
          </div>
        )}
      </div>

      {/* Summary Score Banner */}
      {summary && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white p-5 rounded-2xl shadow-sm flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-blue-100 uppercase">Aggregate Marks</p>
              <h3 className="text-2xl font-bold mt-1">
                {summary.total_obtained || 0} <span className="text-sm font-normal text-blue-200">/ {summary.total_max || 600}</span>
              </h3>
            </div>
            <Award className="w-10 h-10 text-white/40" />
          </div>

          <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-slate-400 uppercase">Overall Percentage</p>
              <h3 className="text-2xl font-bold text-slate-800 mt-1">{summary.percentage || 0}%</h3>
            </div>
            <Percent className="w-10 h-10 text-blue-500/20" />
          </div>

          <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-slate-400 uppercase">Overall Grade</p>
              <h3 className="text-2xl font-black text-indigo-700 mt-1">Grade {summary.grade || 'N/A'}</h3>
            </div>
            <span className={`px-3 py-1 rounded-xl text-xs font-bold border ${getGradeColor(summary.grade)}`}>
              {summary.grade === 'F' ? 'Probation' : 'Promoted'}
            </span>
          </div>
        </div>
      )}

      {/* Marks Breakdown Table */}
      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden">
        <div className="p-4 border-b border-slate-100 flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-800">Academic Subject Performance Breakdown</h3>
          <span className="text-xs text-slate-500 font-medium">Session: 2025-2026 (Final Term)</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50/75 border-b border-slate-200 text-[11px] font-bold uppercase tracking-wider text-slate-500">
                <th className="py-3 px-4">Subject</th>
                <th className="py-3 px-4">Marks Obtained</th>
                <th className="py-3 px-4">Total Marks</th>
                <th className="py-3 px-4">Percentage</th>
                <th className="py-3 px-4">Grade</th>
                <th className="py-3 px-4">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-xs text-slate-700">
              {loading ? (
                <tr>
                  <td colSpan="6" className="text-center py-8 text-slate-400">Loading student marks...</td>
                </tr>
              ) : results.length === 0 ? (
                <tr>
                  <td colSpan="6" className="text-center py-8 text-slate-400">No marks recorded yet for this student.</td>
                </tr>
              ) : (
                results.map((r) => (
                  <tr key={r.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-3.5 px-4 font-bold text-slate-900">{r.subject}</td>
                    <td className="py-3.5 px-4 font-semibold text-slate-800">{r.marks_obtained}</td>
                    <td className="py-3.5 px-4 text-slate-500">{r.total_marks}</td>
                    <td className="py-3.5 px-4 font-mono font-medium">{r.percentage}%</td>
                    <td className="py-3.5 px-4">
                      <span className={`px-2.5 py-0.5 rounded-md text-xs font-bold border ${getGradeColor(r.grade)}`}>
                        {r.grade}
                      </span>
                    </td>
                    <td className="py-3.5 px-4">
                      {r.marks_obtained >= 40 ? (
                        <span className="text-emerald-600 font-semibold flex items-center gap-1">
                          <CheckCircle2 className="w-3.5 h-3.5" /> Pass
                        </span>
                      ) : (
                        <span className="text-rose-600 font-semibold flex items-center gap-1">
                          <AlertCircle className="w-3.5 h-3.5" /> Fail (&lt;40%)
                        </span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Enter / Update Marks Modal */}
      {isEntryOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-100">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100 mb-4">
              <h3 className="text-base font-bold text-slate-900">Record Subject Marks</h3>
              <button onClick={() => setIsEntryOpen(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            {entryMsg && (
              <div className="mb-4 p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs">
                {entryMsg}
              </div>
            )}

            <form onSubmit={handleSaveMarks} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Subject</label>
                <select
                  value={entryForm.subject}
                  onChange={(e) => setEntryForm({ ...entryForm, subject: e.target.value })}
                  className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-600"
                >
                  {SUBJECTS.map(subj => (
                    <option key={subj} value={subj}>{subj}</option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Marks Obtained</label>
                  <input
                    type="number"
                    step="0.5"
                    min="0"
                    max={entryForm.total_marks}
                    required
                    value={entryForm.marks_obtained}
                    onChange={(e) => setEntryForm({ ...entryForm, marks_obtained: e.target.value })}
                    className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-600"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Total Marks</label>
                  <input
                    type="number"
                    required
                    value={entryForm.total_marks}
                    onChange={(e) => setEntryForm({ ...entryForm, total_marks: e.target.value })}
                    className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-600"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Exam Type</label>
                <select
                  value={entryForm.exam_type}
                  onChange={(e) => setEntryForm({ ...entryForm, exam_type: e.target.value })}
                  className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-600"
                >
                  <option value="Final Term">Final Term Examination</option>
                  <option value="Midterm">Midterm Examination</option>
                </select>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setIsEntryOpen(false)}
                  className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-xl"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 text-xs font-bold text-white bg-blue-600 hover:bg-blue-700 rounded-xl shadow-sm"
                >
                  Save Marks
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
