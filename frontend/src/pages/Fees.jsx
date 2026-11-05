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
import PdfButton from '../components/PdfButton';
import { apiErrorMessage } from '../lib/errors';
import {
  challanFormError,
  defaultDueDate,
  formatRupees,
  monthLabel,
  monthPickerValue,
  paymentAmountError,
} from '../lib/fees';

const DEFAULT_FEE_AMOUNT = 4000;
const STATUS_FILTERS = ['all', 'pending', 'partial', 'paid'];

function newChallanForm(studentId = '') {
  const month = monthPickerValue();
  return { student_id: studentId, amount: DEFAULT_FEE_AMOUNT, month, due_date: defaultDueDate(month) };
}

export default function Fees() {
  const [invoices, setInvoices] = useState([]);
  const [students, setStudents] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('all');
  const [search, setSearch] = useState('');

  // Generate Challan Modal
  const [isGenerateOpen, setIsGenerateOpen] = useState(false);
  const [challanForm, setChallanForm] = useState(() => newChallanForm());
  const [generateError, setGenerateError] = useState('');
  const [generating, setGenerating] = useState(false);

  // Pay Modal
  const [payingInvoice, setPayingInvoice] = useState(null);
  const [paymentMode, setPaymentMode] = useState('cash');
  const [paymentAmount, setPaymentAmount] = useState('');
  const [paymentError, setPaymentError] = useState('');
  const [paying, setPaying] = useState(false);
  const [paymentHistory, setPaymentHistory] = useState([]);

  useEffect(() => {
    fetchInvoices();
    fetchSummary();
    fetchStudentsList();
  }, [statusFilter]);

  const fetchSummary = async () => {
    try {
      const res = await api.getFeeSummary();
      setSummary(res.data);
    } catch (err) {
      console.error('Error fetching fee summary:', err);
    }
  };

  const refreshFees = () => {
    fetchInvoices();
    fetchSummary();
  };

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

  const openGenerateDialog = () => {
    setChallanForm(newChallanForm(challanForm.student_id));
    setGenerateError('');
    setIsGenerateOpen(true);
  };

  const handleChallanMonthChange = (month) => {
    setChallanForm((form) => ({ ...form, month, due_date: month ? defaultDueDate(month) : '' }));
  };

  const handleGenerateChallan = async (e) => {
    e.preventDefault();
    const problem = challanFormError(challanForm);
    setGenerateError(problem || '');
    if (problem) return;

    setGenerating(true);
    try {
      await api.generateChallan({
        student_id: parseInt(challanForm.student_id),
        amount: parseFloat(challanForm.amount),
        month: monthLabel(challanForm.month),
        due_date: challanForm.due_date
      });
      setIsGenerateOpen(false);
      refreshFees();
    } catch (err) {
      setGenerateError(apiErrorMessage(err, 'Could not issue the challan. Please check the details.'));
    } finally {
      setGenerating(false);
    }
  };

  const openPaymentDialog = async (invoice) => {
    setPayingInvoice(invoice);
    setPaymentAmount(String(invoice.balance));
    setPaymentMode('cash');
    setPaymentError('');
    setPaymentHistory([]);
    if (invoice.amount_paid > 0) {
      try {
        const res = await api.getInvoicePayments(invoice.id);
        setPaymentHistory(res.data);
      } catch (err) {
        console.error('Error fetching payment history:', err);
      }
    }
  };

  const handleConfirmPayment = async () => {
    if (!payingInvoice || paying) return;
    const problem = paymentAmountError(paymentAmount, payingInvoice.balance);
    setPaymentError(problem || '');
    if (problem) return;

    setPaying(true);
    try {
      await api.payInvoice(payingInvoice.id, {
        amount_paid: parseFloat(paymentAmount),
        payment_mode: paymentMode
      });
      setPayingInvoice(null);
      refreshFees();
    } catch (err) {
      setPaymentError(apiErrorMessage(err, 'The payment could not be recorded. Please try again.'));
      refreshFees();
    } finally {
      setPaying(false);
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
          onClick={openGenerateDialog}
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
            <h4 className="text-lg font-bold text-slate-800">{summary?.invoice_count ?? 0} Challans</h4>
          </div>
        </div>
        <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-xs flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center font-bold">
            <CheckCircle2 className="w-5 h-5" />
          </div>
          <div>
            <p className="text-[11px] font-semibold text-slate-400 uppercase">Recovered Amount</p>
            <h4 className="text-lg font-bold text-emerald-700">{formatRupees(summary?.collected)}</h4>
          </div>
        </div>
        <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-xs flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-rose-50 text-rose-600 flex items-center justify-center font-bold">
            <Clock className="w-5 h-5" />
          </div>
          <div>
            <p className="text-[11px] font-semibold text-slate-400 uppercase">Outstanding Balance</p>
            <h4 className="text-lg font-bold text-rose-700">{formatRupees(summary?.outstanding)}</h4>
            <p className="text-[11px] text-slate-500">{formatRupees(summary?.overdue)} overdue</p>
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
          {STATUS_FILTERS.map((s) => (
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
                      <div className="font-bold text-slate-900">
                        {inv.student_name}
                        {inv.student_archived && (
                          <span className="ml-1.5 px-1.5 py-0.5 rounded bg-slate-100 border border-slate-200 text-[10px] font-semibold text-slate-600">
                            Archived
                          </span>
                        )}
                      </div>
                      <div className="text-[11px] text-slate-500">
                        Roll: #{inv.roll_number} &bull; {inv.grade}-{inv.section}
                      </div>
                    </td>
                    <td className="py-3.5 px-4 font-medium text-slate-800">
                      {inv.month}
                    </td>
                    <td className="py-3.5 px-4">
                      <div className="font-bold text-slate-900">{formatRupees(inv.amount)}</div>
                      {inv.amount_paid > 0 && inv.balance > 0 && (
                        <div className="text-[11px] text-slate-500">
                          Paid {formatRupees(inv.amount_paid)} &bull; <span className="font-semibold text-rose-700">Owes {formatRupees(inv.balance)}</span>
                        </div>
                      )}
                    </td>
                    <td className="py-3.5 px-4 font-medium text-slate-600">
                      <div>{inv.due_date}</div>
                      {inv.is_overdue && <div className="text-[11px] font-bold text-rose-700">Overdue</div>}
                    </td>
                    <td className="py-3.5 px-4">
                      {inv.status === 'paid' ? (
                        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">
                          <CheckCircle2 className="w-3 h-3" /> Paid
                        </span>
                      ) : inv.status === 'partial' ? (
                        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-bold bg-amber-100 text-amber-800 border border-amber-200">
                          <Clock className="w-3 h-3" /> Part Paid
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-bold bg-rose-100 text-rose-800 border border-rose-200">
                          <Clock className="w-3 h-3" /> Pending
                        </span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-right space-x-2 whitespace-nowrap">
                      {inv.status !== 'paid' && (
                        <button
                          onClick={() => openPaymentDialog(inv)}
                          className="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-[11px] font-bold shadow-xs transition-colors"
                        >
                          Record Payment
                        </button>
                      )}

                      {/* Download PDF Challan */}
                      <PdfButton
                        fetchPdf={() => api.getChallanPdf(inv.id)}
                        className="inline-flex items-center gap-1 px-2.5 py-1 bg-blue-50 text-blue-700 hover:bg-blue-100 border border-blue-200 rounded-lg text-[11px] font-bold transition-colors"
                        title="Download Official 2-Part Fee Challan PDF"
                      >
                        <Download className="w-3 h-3" />
                        <span>Challan PDF</span>
                      </PdfButton>
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
                  <label htmlFor="challan-month" className="block text-xs font-bold text-slate-700 mb-1">Month</label>
                  <input
                    id="challan-month"
                    type="month"
                    required
                    value={challanForm.month}
                    onChange={(e) => handleChallanMonthChange(e.target.value)}
                    className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-600"
                  />
                </div>
                <div>
                  <label htmlFor="challan-amount" className="block text-xs font-bold text-slate-700 mb-1">Total Fee (PKR)</label>
                  <input
                    id="challan-amount"
                    type="number"
                    min="1"
                    required
                    value={challanForm.amount}
                    onChange={(e) => setChallanForm({ ...challanForm, amount: e.target.value })}
                    className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-600"
                  />
                </div>
              </div>

              <div>
                <label htmlFor="challan-due-date" className="block text-xs font-bold text-slate-700 mb-1">Due Date</label>
                <input
                  id="challan-due-date"
                  type="date"
                  required
                  value={challanForm.due_date}
                  onChange={(e) => setChallanForm({ ...challanForm, due_date: e.target.value })}
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
                  disabled={generating}
                  className="px-5 py-2 text-xs font-bold text-white bg-blue-600 hover:bg-blue-700 rounded-xl shadow-sm disabled:opacity-60"
                >
                  {generating ? 'Issuing…' : 'Generate Challan'}
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
              Payment for <b>{payingInvoice.student_name}</b> ({payingInvoice.challan_number})
            </p>

            {paymentError && (
              <div role="alert" className="mt-3 p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{paymentError}</span>
              </div>
            )}

            <div className="my-4 p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs space-y-1">
              <div className="flex justify-between">
                <span className="text-slate-500">Invoice Total:</span>
                <span className="font-semibold text-slate-700">{formatRupees(payingInvoice.amount)}</span>
              </div>
              {payingInvoice.amount_paid > 0 && (
                <div className="flex justify-between">
                  <span className="text-slate-500">Already Paid:</span>
                  <span className="font-semibold text-slate-700">{formatRupees(payingInvoice.amount_paid)}</span>
                </div>
              )}
              <div className="flex justify-between">
                <span className="text-slate-500">Still Owed:</span>
                <span className="font-bold text-slate-900">{formatRupees(payingInvoice.balance)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Billing Month:</span>
                <span className="font-semibold text-slate-700">{payingInvoice.month}</span>
              </div>
            </div>

            {paymentHistory.length > 0 && (
              <div className="mb-4 text-xs">
                <p className="font-bold text-slate-700 mb-1">Earlier Payments</p>
                <ul className="space-y-1 text-slate-600">
                  {paymentHistory.map((payment) => (
                    <li key={payment.id} className="flex justify-between">
                      <span className="capitalize">{payment.payment_mode} &bull; {new Date(payment.paid_at).toLocaleDateString()}</span>
                      <span className="font-semibold">{formatRupees(payment.amount_paid)}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <div className="mb-4">
              <label htmlFor="payment-amount" className="block text-xs font-bold text-slate-700 mb-1">Amount Received (PKR)</label>
              <input
                id="payment-amount"
                type="number"
                min="1"
                max={payingInvoice.balance}
                step="any"
                value={paymentAmount}
                onChange={(e) => setPaymentAmount(e.target.value)}
                className="w-full px-3 py-2 text-sm bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-600"
              />
              <p className="text-[11px] text-slate-500 mt-1">Enter less than the full amount to record part payment.</p>
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
                disabled={paying}
                className="px-4 py-1.5 text-xs font-bold text-white bg-emerald-600 hover:bg-emerald-700 rounded-xl shadow-xs disabled:opacity-60"
              >
                {paying ? 'Saving…' : 'Confirm Payment'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
