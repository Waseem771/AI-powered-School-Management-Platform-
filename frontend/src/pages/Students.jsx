import React, { useState, useEffect } from 'react';
import {
  Users,
  Search,
  UserPlus,
  Edit2,
  Trash2,
  FileText,
  X,
  Phone,
  Calendar,
  AlertCircle,
  GraduationCap,
  Archive,
  ArchiveRestore
} from 'lucide-react';
import { api } from '../api/client';
import PdfButton from '../components/PdfButton';
import { apiErrorMessage } from '../lib/errors';

const GRADES = ["All Grades", "Grade 6", "Grade 7", "Grade 8", "Grade 9", "Grade 10"];
const SECTIONS = ["A", "B"];
const VIEWS = [
  { id: 'active', label: 'Current Students' },
  { id: 'archived', label: 'Archived' }
];
const EMPTY_FORM = {
  name: '',
  roll_number: '',
  grade: 'Grade 8',
  section: 'A',
  guardian_name: '',
  phone: '',
  dob: ''
};

export default function Students() {
  const [students, setStudents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [search, setSearch] = useState('');
  const [selectedGrade, setSelectedGrade] = useState('All Grades');
  const [view, setView] = useState('active');

  // Modals state
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [editingStudent, setEditingStudent] = useState(null);
  const [formError, setFormError] = useState('');
  // { type: 'archive' | 'restore' | 'delete', student } while a confirmation is open.
  const [pendingAction, setPendingAction] = useState(null);
  const [actionError, setActionError] = useState('');
  const [actionBusy, setActionBusy] = useState(false);

  const [formData, setFormData] = useState(EMPTY_FORM);

  useEffect(() => {
    fetchStudents();
  }, [selectedGrade, view]);

  const fetchStudents = async () => {
    try {
      setLoading(true);
      setLoadError('');
      const params = { status: view };
      if (selectedGrade !== 'All Grades') params.grade = selectedGrade;
      if (search) params.search = search;
      const res = await api.getStudents(params);
      setStudents(res.data);
    } catch (err) {
      setStudents([]);
      setLoadError(apiErrorMessage(err, 'Could not load students. Please try again.'));
    } finally {
      setLoading(false);
    }
  };

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    fetchStudents();
  };

  const handleCreateStudent = async (e) => {
    e.preventDefault();
    setFormError('');
    try {
      await api.createStudent(formData);
      setIsAddOpen(false);
      resetForm();
      fetchStudents();
    } catch (err) {
      setFormError(apiErrorMessage(err, 'Failed to create student.'));
    }
  };

  const handleUpdateStudent = async (e) => {
    e.preventDefault();
    setFormError('');
    try {
      await api.updateStudent(editingStudent.id, formData);
      setIsEditOpen(false);
      setEditingStudent(null);
      resetForm();
      fetchStudents();
    } catch (err) {
      setFormError(apiErrorMessage(err, 'Failed to update student.'));
    }
  };

  const askToConfirm = (type, student) => {
    setActionError('');
    setPendingAction({ type, student });
  };

  const handleConfirmedAction = async () => {
    const { type, student } = pendingAction;
    const calls = { archive: api.archiveStudent, restore: api.restoreStudent, delete: api.deleteStudent };
    setActionBusy(true);
    setActionError('');
    try {
      await calls[type](student.id);
      setPendingAction(null);
      fetchStudents();
    } catch (err) {
      setActionError(apiErrorMessage(err, 'That did not work. Please try again.'));
    } finally {
      setActionBusy(false);
    }
  };

  const openEditModal = (s) => {
    setEditingStudent(s);
    setFormData({
      name: s.name,
      roll_number: s.roll_number,
      grade: s.grade,
      section: s.section,
      guardian_name: s.guardian_name,
      phone: s.phone,
      dob: s.dob || ''
    });
    setFormError('');
    setIsEditOpen(true);
  };

  const resetForm = () => {
    setFormData(EMPTY_FORM);
    setFormError('');
  };

  const filteredStudents = students.filter(s => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      s.name.toLowerCase().includes(q) ||
      s.roll_number.toLowerCase().includes(q) ||
      s.guardian_name.toLowerCase().includes(q) ||
      s.phone.includes(q)
    );
  });

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Student Enrollment Registry</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Manage student biodata, section assignments, and academic records.
          </p>
        </div>
        <button
          onClick={() => { resetForm(); setIsAddOpen(true); }}
          className="inline-flex items-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-bold shadow-sm transition-all"
        >
          <UserPlus className="w-4 h-4" />
          <span>Register New Student</span>
        </button>
      </div>

      {/* Current or archived students */}
      <div className="flex items-center gap-2" role="tablist" aria-label="Which students to show">
        {VIEWS.map((option) => (
          <button
            key={option.id}
            role="tab"
            aria-selected={view === option.id}
            onClick={() => setView(option.id)}
            className={`px-3.5 py-2 rounded-xl text-xs font-bold transition-colors ${
              view === option.id
                ? 'bg-blue-600 text-white shadow-xs'
                : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'
            }`}
          >
            {option.label}
          </button>
        ))}
      </div>

      {loadError && (
        <div role="alert" className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
          <span>{loadError}</span>
          <button onClick={fetchStudents} className="ml-auto font-bold underline">Try again</button>
        </div>
      )}

      {/* Filter & Search Toolbar */}
      <div className="bg-white p-4 rounded-2xl border border-slate-200/80 shadow-xs flex flex-col md:flex-row gap-3 items-center justify-between">
        <form onSubmit={handleSearchSubmit} className="relative w-full md:w-96">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by name, roll number, or phone..."
            className="w-full pl-10 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:bg-white"
          />
        </form>

        <div className="flex items-center gap-2 overflow-x-auto w-full md:w-auto pb-1 md:pb-0">
          {GRADES.map((g) => (
            <button
              key={g}
              onClick={() => setSelectedGrade(g)}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap transition-colors ${
                selectedGrade === g
                  ? 'bg-slate-900 text-white shadow-xs'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              {g}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50/75 border-b border-slate-200 text-[11px] font-bold uppercase tracking-wider text-slate-500">
                <th className="py-3.5 px-4">Roll No</th>
                <th className="py-3.5 px-4">Student Name</th>
                <th className="py-3.5 px-4">Grade & Section</th>
                <th className="py-3.5 px-4">Guardian Name</th>
                <th className="py-3.5 px-4">Contact Phone</th>
                <th className="py-3.5 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-xs text-slate-700">
              {loading ? (
                <tr>
                  <td colSpan="6" className="text-center py-10 text-slate-400">
                    Loading student records...
                  </td>
                </tr>
              ) : filteredStudents.length === 0 ? (
                <tr>
                  <td colSpan="6" className="text-center py-10 text-slate-400">
                    {view === 'archived' ? 'No archived students.' : 'No matching student records found.'}
                  </td>
                </tr>
              ) : (
                filteredStudents.map((s) => (
                  <tr key={s.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-3.5 px-4 font-mono font-bold text-blue-700">
                      #{s.roll_number}
                    </td>
                    <td className="py-3.5 px-4">
                      <div className="font-bold text-slate-900">{s.name}</div>
                      <div className="text-[10px] text-slate-400 flex items-center gap-1">
                        <Calendar className="w-3 h-3" />
                        <span>DOB: {s.dob || 'N/A'}</span>
                      </div>
                    </td>
                    <td className="py-3.5 px-4">
                      <span className="inline-flex items-center px-2 py-0.5 rounded-md font-semibold bg-slate-100 text-slate-800 border border-slate-200">
                        {s.grade} - {s.section}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 font-medium text-slate-800">
                      {s.guardian_name}
                    </td>
                    <td className="py-3.5 px-4 text-slate-600 font-mono text-[11px]">
                      {s.phone}
                    </td>
                    <td className="py-3.5 px-4 text-right space-x-1.5 whitespace-nowrap">
                      {/* Report Card PDF trigger */}
                      <PdfButton
                        fetchPdf={() => api.getReportCardPdf(s.id)}
                        title="Download Report Card PDF"
                        className="inline-flex items-center gap-1 px-2 py-1 rounded-lg bg-indigo-50 text-indigo-700 hover:bg-indigo-100 border border-indigo-200 text-[11px] font-semibold"
                      >
                        <GraduationCap className="w-3.5 h-3.5" />
                        <span>Report Card</span>
                      </PdfButton>
                      <button
                        onClick={() => openEditModal(s)}
                        title="Edit Student"
                        aria-label={`Edit ${s.name}`}
                        className="p-1 rounded-lg text-slate-500 hover:text-blue-600 hover:bg-slate-100 transition-colors"
                      >
                        <Edit2 className="w-4 h-4" />
                      </button>
                      {view === 'active' ? (
                        <button
                          onClick={() => askToConfirm('archive', s)}
                          title="Archive Student"
                          aria-label={`Archive ${s.name}`}
                          className="p-1 rounded-lg text-slate-400 hover:text-amber-700 hover:bg-amber-50 transition-colors"
                        >
                          <Archive className="w-4 h-4" />
                        </button>
                      ) : (
                        <>
                          <button
                            onClick={() => askToConfirm('restore', s)}
                            title="Restore Student"
                            aria-label={`Restore ${s.name}`}
                            className="p-1 rounded-lg text-slate-400 hover:text-emerald-700 hover:bg-emerald-50 transition-colors"
                          >
                            <ArchiveRestore className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => askToConfirm('delete', s)}
                            title="Delete Permanently"
                            aria-label={`Delete ${s.name} permanently`}
                            className="p-1 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition-colors"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        <div className="p-4 border-t border-slate-100 bg-slate-50/50 flex items-center justify-between text-xs text-slate-500">
          <span>Showing {filteredStudents.length} {view === 'archived' ? 'archived' : 'current'} students</span>
        </div>
      </div>

      {/* Archive / Restore / Delete confirmation */}
      {pendingAction && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div role="dialog" aria-modal="true" aria-labelledby="student-action-title" className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-100">
            <h3 id="student-action-title" className="text-base font-bold text-slate-900">
              {pendingAction.type === 'archive' && `Archive ${pendingAction.student.name}?`}
              {pendingAction.type === 'restore' && `Restore ${pendingAction.student.name}?`}
              {pendingAction.type === 'delete' && `Permanently delete ${pendingAction.student.name}?`}
            </h3>
            <p className="text-xs text-slate-600 mt-2 leading-relaxed">
              {pendingAction.type === 'archive' &&
                'For a student who has left. They leave the current lists and counts. Their fee records, payments, and exam marks are kept, and you can restore them at any time.'}
              {pendingAction.type === 'restore' &&
                'They return to the current lists and counts, with all their records.'}
              {pendingAction.type === 'delete' &&
                'Only for a record entered by mistake. This cannot be undone, and it is refused if the student has any fee or exam records.'}
            </p>

            {actionError && (
              <div role="alert" className="mt-3 p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
                <span>{actionError}</span>
              </div>
            )}

            <div className="flex items-center justify-end gap-3 pt-4 mt-4 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setPendingAction(null)}
                className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-xl transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirmedAction}
                disabled={actionBusy}
                className={`px-5 py-2 text-xs font-bold text-white rounded-xl shadow-sm transition-colors disabled:opacity-60 ${
                  pendingAction.type === 'delete' ? 'bg-rose-600 hover:bg-rose-700' : 'bg-blue-600 hover:bg-blue-700'
                }`}
              >
                {pendingAction.type === 'archive' && 'Archive Student'}
                {pendingAction.type === 'restore' && 'Restore Student'}
                {pendingAction.type === 'delete' && 'Delete Permanently'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add / Edit Student Modal */}
      {(isAddOpen || isEditOpen) && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-100">
            <div className="flex items-center justify-between pb-4 border-b border-slate-100 mb-4">
              <h3 className="text-lg font-bold text-slate-900">
                {isAddOpen ? 'Register New Student' : `Edit Student: ${editingStudent?.name}`}
              </h3>
              <button
                onClick={() => { setIsAddOpen(false); setIsEditOpen(false); }}
                className="text-slate-400 hover:text-slate-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {formError && (
              <div className="mb-4 p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
                <span>{formError}</span>
              </div>
            )}

            <form onSubmit={isAddOpen ? handleCreateStudent : handleUpdateStudent} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Full Name</label>
                  <input
                    type="text"
                    required
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="e.g. Ahmed Khan"
                    className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-600 focus:bg-white"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Roll Number</label>
                  <input
                    type="text"
                    required
                    value={formData.roll_number}
                    onChange={(e) => setFormData({ ...formData, roll_number: e.target.value })}
                    placeholder="e.g. 045"
                    className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-600 focus:bg-white"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Grade</label>
                  <select
                    value={formData.grade}
                    onChange={(e) => setFormData({ ...formData, grade: e.target.value })}
                    className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-600 focus:bg-white"
                  >
                    {GRADES.filter(g => g !== 'All Grades').map(g => (
                      <option key={g} value={g}>{g}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Section</label>
                  <select
                    value={formData.section}
                    onChange={(e) => setFormData({ ...formData, section: e.target.value })}
                    className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-600 focus:bg-white"
                  >
                    {SECTIONS.map(s => (
                      <option key={s} value={s}>Section {s}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Guardian Name</label>
                  <input
                    type="text"
                    required
                    value={formData.guardian_name}
                    onChange={(e) => setFormData({ ...formData, guardian_name: e.target.value })}
                    placeholder="e.g. Tariq Khan"
                    className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-600 focus:bg-white"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Contact Phone</label>
                  <input
                    type="text"
                    required
                    value={formData.phone}
                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                    placeholder="e.g. 0300-5551234"
                    className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-600 focus:bg-white"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Date of Birth (optional)</label>
                <input
                  type="date"
                  value={formData.dob}
                  onChange={(e) => setFormData({ ...formData, dob: e.target.value })}
                  className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-600 focus:bg-white"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => { setIsAddOpen(false); setIsEditOpen(false); }}
                  className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-xl transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 text-xs font-bold text-white bg-blue-600 hover:bg-blue-700 rounded-xl shadow-sm transition-colors"
                >
                  {isAddOpen ? 'Save & Register' : 'Update Record'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
