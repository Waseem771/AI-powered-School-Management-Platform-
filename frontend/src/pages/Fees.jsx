import React, { useState, useEffect } from 'react';
import {
  Receipt,
  Download,
  CheckCircle2,
  Clock,
  Plus,
  Search,
  Filter,
  CreditCard,
  Building2,
  Banknote,
  X,
  AlertCircle
} from 'lucide-react';
import { api } from '../api/client';

export default function Fees() {
  const [invoices, setInvoices] = useState([]);
  const [students, setStudents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('all');
  const [search, setSearch] = useState('');

  // Generate Challan Modal
  const [isGenerateOpen, setIsGenerateOpen] = useState(false);
  const [challanForm, setChallanForm] = useState({
    student_id: '',
    amount: 4000,
    month: 'November 2025',
    due_date: '10-Nov-2025'
  });
  const [generateError, setGenerateError] = useState('');

  // Pay Modal
  const [payingInvoice, setPayingInvoice] = useState(null);
  const [paymentMode, setPaymentMode] = useState('cash');

  useEffect(() => {
    fetchInvoices();
    fetchStudentsList();
  }, [statusFilter]);

  const fetchInvoices = async () => {
    try {
      setLoading(true);
      const params = {};
      if (statusFilter !== 'all') params.status = statusFilter;
      const res = await api.getFees(params);
      setInvoices(res.data);
    } catch (err) {
      console.error('Error fetching fees:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchStudentsList = async () => {
    try {
      const res = await api.getStudents();
      setStudents(res.data);
      if (res.data.length > 0 && !challanForm.student_id) {
        setChallanForm(prev => ({ ...prev, student_id: res.data[0].id }));
      }
    } catch (err) {
      console.error('Error fetching students for fees:', err);
    }
  };

  const handleGenerateChallan = async (e) => {
    e.preventDefault();
    setGenerateError('');
    try {
      await api.generateChallan({
        student_id: parseInt(challanForm.student_id),
        amount: parseFloat(challanForm.amount),
        month: challanForm.month,
        due_date: challanForm.due_date
      });
      setIsGenerateOpen(false);
      fetchInvoices();
    } catch (err) {
      setGenerateError(err.response?.data?.detail || 'Failed to generate challan.');
    }
  };

  const handleConfirmPayment = async () => {
    if (!payingInvoice) return;
    try {
      await api.payInvoice(payingInvoice.id, {
        amount_paid: payingInvoice.amount,
        payment_mode: paymentMode
      });
      setPayingInvoice(null);
      fetchInvoices();
    } catch (err) {
      alert('Payment processing failed.');
    }
  };

  const filteredInvoices = invoices.filter(inv => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      inv.challan_number.toLowerCase().includes(q) ||
      inv.student_name.toLowerCase().includes(q) ||
      inv.roll_number.toLowerCase().includes(q)
    );
  });

  const totalCollected = invoices
    .filter(i => i.status === 'paid')
    .reduce((acc, curr) => acc + curr.amount, 0);

  const totalPending = invoices
    .filter(i => i.status === 'pending')
    .reduce((acc, curr) => acc + curr.amount, 0);

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Fee Challans & Billing</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Issue monthly tuition challans, process payments, and generate official 2-copy PDFs.
          </p>
        </div>
        <button
          onClick={() => setIsGenerateOpen(true)}
          className="inline-flex items-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-bold shadow-sm transition-all"
        >
          <Plus className="w-4 h-4" />
          <span>Issue New Challan</span>
        </button>
      </div>

      {/* Summary Mini Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-xs flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center font-bold">
            <Receipt className="w-5 h-5" />
          </div>
          <div>
            <p className="text-[11px] font-semibold text-slate-400 uppercase">Total Invoices</p>
            <h4 className="text-lg font-bold text-slate-800">{invoices.length} Challans</h4>
          </div>
        </div>
        <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-xs flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center font-bold">
            <CheckCircle2 className="w-5 h-5" />
          </div>
          <div>
            <p className="text-[11px] font-semibold text-slate-400 uppercase">Recovered Amount</p>
            <h4 className="text-lg font-bold text-emerald-700">Rs. {totalCollected.toLocaleString()}</h4>
          </div>
        </div>
        <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-xs flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-rose-50 text-rose-600 flex items-center justify-center font-bold">
            <Clock className="w-5 h-5" />
          </div>
          <div>
            <p className="text-[11px] font-semibold text-slate-400 uppercase">Pending Receivables</p>
            <h4 className="text-lg font-bold text-rose-700">Rs. {totalPending.toLocaleString()}</h4>
          </div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white p-4 rounded-2xl border border-slate-200/80 shadow-xs flex flex-col md:flex-row gap-3 items-center justify-between">
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search challan number or student..."
            className="w-full pl-10 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:bg-white"
          />
        </div>

        <div className="flex items-center gap-2">
          {['all', 'pending', 'paid'].map((s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold uppercase tracking-wider transition-colors ${
                statusFilter === s
                  ? 'bg-slate-900 text-white shadow-xs'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* Invoices Table */}
      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50/75 border-b border-slate-200 text-[11px] font-bold uppercase tracking-wider text-slate-500">
                <th className="py-3.5 px-4">Challan No</th>
                <th className="py-3.5 px-4">Student Info</th>
                <th className="py-3.5 px-4">Billing Month</th>
                <th className="py-3.5 px-4">Total Amount</th>
                <th className="py-3.5 px-4">Due Date</th>
                <th className="py-3.5 px-4">Payment Status</th>
                <th className="py-3.5 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-xs text-slate-700">
              {loading ? (
                <tr>
                  <td colSpan="7" className="text-center py-10 text-slate-400">
                    Loading invoices...
                  </td>
                </tr>
              ) : filteredInvoices.length === 0 ? (
                <tr>
                  <td colSpan="7" className="text-center py-10 text-slate-400">
                    No matching fee records found.
                  </td>
                </tr>
              ) : (
                filteredInvoices.map((inv) => (
                  <tr key={inv.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-3.5 px-4 font-mono font-bold text-slate-900">
                      {inv.challan_number}
                    </td>
                    <td className="py-3.5 px-4">
                      <div className="font-bold text-slate-900">{inv.student_name}</div>
                      <div className="text-[11px] text-slate-500">
                        Roll: #{inv.roll_number} &bull; {inv.grade}-{inv.section}
                      </div>
                    </td>
                    <td className="py-3.5 px-4 font-medium text-slate-800">
                      {inv.month}
                    </td>
                    <td className="py-3.5 px-4 font-bold text-slate-900">
                      Rs. {inv.amount.toLocaleString()}
                    </td>
                    <td className="py-3.5 px-4 font-medium text-slate-600">
                      {inv.due_date}
                    </td>
                    <td className="py-3.5 px-4">
                      {inv.status === 'paid' ? (
                        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">
                          <CheckCircle2 className="w-3 h-3" /> Paid
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-bold bg-rose-100 text-rose-800 border border-rose-200">
                          <Clock className="w-3 h-3" /> Pending
                        </span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-right space-x-2 whitespace-nowrap">
                      {/* Mark Paid Button */}
                      {inv.status === 'pending' && (
                        <button
                          onClick={() => setPayingInvoice(inv)}
                          className="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-[11px] font-bold shadow-xs transition-colors"
                        >
                          Mark Paid
                        </button>
                      )}

                      {/* Download PDF Challan */}
                      <a
                        href={api.getChallanPdfUrl(inv.id)}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1 px-2.5 py-1 bg-blue-50 text-blue-700 hover:bg-blue-100 border border-blue-200 rounded-lg text-[11px] font-bold transition-colors"
                        title="Download Official 2-Part Fee Challan PDF"
                      >
                        <Download className="w-3 h-3" />
                        <span>Challan PDF</span>
                      </a>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Generate Challan Modal */}
      {isGenerateOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-100">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100 mb-4">
              <h3 className="text-base font-bold text-slate-900">Issue Fee Challan</h3>
              <button onClick={() => setIsGenerateOpen(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            {generateError && (
              <div className="mb-4 p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{generateError}</span>
              </div>
            )}

            <form onSubmit={handleGenerateChallan} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Select Student</label>
                <select
                  value={challanForm.student_id}
                  onChange={(e) => setChallanForm({ ...challanForm, student_id: e.target.value })}
                  required
                  className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-600"
                >
                  {students.map(s => (
                    <option key={s.id} value={s.id}>
                      #{s.roll_number} - {s.name} ({s.grade}-{s.section})
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Month</label>
                  <input
                    type="text"
                    required
                    value={challanForm.month}
                    onChange={(e) => setChallanForm({ ...challanForm, month: e.target.value })}
                    placeholder="e.g. November 2025"
                    className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-600"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Total Fee (PKR)</label>
                  <input
                    type="number"
                    required
                    value={challanForm.amount}
                    onChange={(e) => setChallanForm({ ...challanForm, amount: e.target.value })}
                    className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-600"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Due Date</label>
                <input
                  type="text"
                  required
                  value={challanForm.due_date}
                  onChange={(e) => setChallanForm({ ...challanForm, due_date: e.target.value })}
                  placeholder="e.g. 10-Nov-2025"
                  className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-600"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setIsGenerateOpen(false)}
                  className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-xl"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 text-xs font-bold text-white bg-blue-600 hover:bg-blue-700 rounded-xl shadow-sm"
                >
                  Generate Challan
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Pay Confirmation Modal */}
      {payingInvoice && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-sm w-full p-6 shadow-2xl border border-slate-100">
            <h3 className="text-base font-bold text-slate-900">Record Fee Payment</h3>
            <p className="text-xs text-slate-500 mt-1">
              Confirming payment for <b>{payingInvoice.student_name}</b> ({payingInvoice.challan_number})
            </p>

            <div className="my-4 p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs space-y-1">
              <div className="flex justify-between">
                <span className="text-slate-500">Amount Due:</span>
                <span className="font-bold text-slate-900">Rs. {payingInvoice.amount.toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Billing Month:</span>
                <span className="font-semibold text-slate-700">{payingInvoice.month}</span>
              </div>
            </div>

            <div className="space-y-2 mb-4">
              <label className="block text-xs font-bold text-slate-700">Payment Mode</label>
              <div className="grid grid-cols-3 gap-2">
                {[
                  { id: 'cash', label: 'Cash', icon: Banknote },
                  { id: 'bank', label: 'Bank', icon: Building2 },
                  { id: 'online', label: 'Online', icon: CreditCard }
                ].map(mode => {
                  const Icon = mode.icon;
                  return (
                    <button
                      key={mode.id}
                      type="button"
                      onClick={() => setPaymentMode(mode.id)}
                      className={`p-2 rounded-xl text-xs font-semibold flex flex-col items-center gap-1 border transition-all ${
                        paymentMode === mode.id
                          ? 'border-blue-600 bg-blue-50 text-blue-700'
                          : 'border-slate-200 text-slate-600 hover:bg-slate-50'
                      }`}
                    >
                      <Icon className="w-4 h-4" />
                      <span>{mode.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setPayingInvoice(null)}
                className="px-3 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-xl"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirmPayment}
                className="px-4 py-1.5 text-xs font-bold text-white bg-emerald-600 hover:bg-emerald-700 rounded-xl shadow-xs"
              >
                Confirm Payment
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
