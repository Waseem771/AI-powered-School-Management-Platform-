import React, { useEffect, useState } from 'react';
import { Banknote, Building2, CheckCircle2, CreditCard, Download } from 'lucide-react';
import { api } from '../api/client';
import { formatDate } from '../lib/activity';
import { apiErrorMessage } from '../lib/errors';
import {
  challanFormError,
  defaultDueDate,
  formatRupees,
  monthLabel,
  monthPickerValue,
  paymentAmountError,
} from '../lib/fees';
import PdfButton from './PdfButton';
import StudentPicker from './StudentPicker';
import Button from './ui/Button';
import { TextField } from './ui/Field';
import Modal from './ui/Modal';
import { EmptyState, ErrorNotice, ErrorState, LoadingState } from './ui/States';

const DEFAULT_FEE_AMOUNT = 4000;
const CHALLAN_FORM_ID = 'challan-form';
const PAYMENT_FORM_ID = 'payment-form';
const PAYMENT_MODES = [
  { id: 'cash', label: 'Cash', icon: Banknote },
  { id: 'bank', label: 'Bank', icon: Building2 },
  { id: 'online', label: 'Online', icon: CreditCard },
];

function ReceiptButton({ paymentId, variant = 'secondary', children }) {
  return (
    <PdfButton variant={variant} fetchPdf={() => api.getReceiptPdf(paymentId)} title="Open the receipt">
      <Download className="h-4 w-4" aria-hidden="true" />
      <span>{children}</span>
    </PdfButton>
  );
}

function usePayments(invoice, enabled) {
  const [payments, setPayments] = useState([]);
  const [loading, setLoading] = useState(enabled);
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (!enabled) return undefined;
    const controller = new AbortController();
    setLoading(true);
    setError('');
    api.getInvoicePayments(invoice.id, { signal: controller.signal })
      .then((res) => { setPayments(res.data); setLoading(false); })
      .catch((err) => {
        if (err.code === 'ERR_CANCELED') return;
        setError(apiErrorMessage(err, 'Earlier payments could not be loaded.'));
        setLoading(false);
      });
    return () => controller.abort();
  }, [invoice.id, enabled, attempt]);

  return { payments, loading, error, retry: () => setAttempt((current) => current + 1) };
}

function PaymentList({ payments }) {
  return (
    <ul className="divide-y divide-slate-200 rounded-xl border border-slate-200">
      {payments.map((payment) => (
        <li key={payment.id} className="flex flex-wrap items-center justify-between gap-2 p-3 text-sm">
          <div>
            <p className="font-bold text-slate-900">{formatRupees(payment.amount_paid)}</p>
            <p className="text-xs capitalize text-slate-600">{payment.payment_mode} &bull; {formatDate(payment.paid_at)} &bull; <span className="normal-case">{payment.receipt_number}</span></p>
          </div>
          <ReceiptButton paymentId={payment.id}>Receipt</ReceiptButton>
        </li>
      ))}
    </ul>
  );
}

/** Pass `initialStudent` when the student is already known, such as on their profile. */
export function IssueChallanDialog({ initialStudent = null, onClose, onIssued }) {
  const [student, setStudent] = useState(initialStudent);
  const [form, setForm] = useState(() => {
    const month = monthPickerValue();
    return { amount: DEFAULT_FEE_AMOUNT, month, due_date: defaultDueDate(month) };
  });
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    const problem = student ? challanFormError(form) : 'Choose the student.';
    setError(problem || '');
    if (problem) return;

    setSaving(true);
    try {
      await api.generateChallan({
        student_id: student.id,
        amount: parseFloat(form.amount),
        month: monthLabel(form.month),
        due_date: form.due_date,
      });
      onIssued(`Challan issued to ${student.name} for ${monthLabel(form.month)}.`);
    } catch (err) {
      setError(apiErrorMessage(err, 'Could not issue the challan. Please check the details.'));
      setSaving(false);
    }
  };

  return (
    <Modal
      title="Issue Fee Challan"
      busy={saving}
      onClose={onClose}
      footer={(
        <>
          <Button variant="ghost" onClick={onClose} disabled={saving}>Cancel</Button>
          <Button type="submit" form={CHALLAN_FORM_ID} disabled={saving}>{saving ? 'Issuing…' : 'Issue Challan'}</Button>
        </>
      )}
    >
      <ErrorNotice>{error}</ErrorNotice>
      <form id={CHALLAN_FORM_ID} onSubmit={handleSubmit} className="space-y-4">
        <StudentPicker student={student} onChange={setStudent} />
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <TextField
            label="Billing month"
            type="month"
            required
            value={form.month}
            onChange={(event) => setForm({ ...form, month: event.target.value, due_date: event.target.value ? defaultDueDate(event.target.value) : '' })}
          />
          <TextField label="Total fee (Rs.)" type="number" min="1" required value={form.amount} onChange={(event) => setForm({ ...form, amount: event.target.value })} />
        </div>
        <TextField label="Due date" type="date" required value={form.due_date} onChange={(event) => setForm({ ...form, due_date: event.target.value })} />
      </form>
    </Modal>
  );
}

/** Stays open after saving, to offer the receipt. `onRecorded` is for refreshing the page behind it. */
export function RecordPaymentDialog({ invoice, onClose, onRecorded }) {
  const [amount, setAmount] = useState(String(invoice.balance));
  const [mode, setMode] = useState('cash');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [recorded, setRecorded] = useState(null);
  const { payments, error: historyError } = usePayments(invoice, invoice.amount_paid > 0);

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (saving) return;
    const problem = paymentAmountError(amount, invoice.balance);
    setError(problem || '');
    if (problem) return;

    setSaving(true);
    try {
      const res = await api.payInvoice(invoice.id, { amount_paid: parseFloat(amount), payment_mode: mode });
      setRecorded(res.data);
      onRecorded();
    } catch (err) {
      setError(apiErrorMessage(err, 'The payment could not be recorded. Please try again.'));
      onRecorded();
    } finally {
      setSaving(false);
    }
  };

  if (recorded) {
    return (
      <Modal
        title="Payment Recorded"
        description={`${invoice.student_name} (${invoice.challan_number})`}
        onClose={onClose}
        footer={(
          <>
            <Button variant="ghost" onClick={onClose}>Done</Button>
            <ReceiptButton paymentId={recorded.payment_id} variant="primary">Print Receipt</ReceiptButton>
          </>
        )}
      >
        <div role="status" className="flex items-start gap-2 rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-900">
          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          <p><b>{formatRupees(recorded.amount_paid)}</b> received, on receipt {recorded.receipt_number}.</p>
        </div>
        <dl className="space-y-1 rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm">
          <div className="flex justify-between gap-4"><dt className="text-slate-600">Paid so far</dt><dd className="font-semibold text-slate-900">{formatRupees(recorded.total_paid)}</dd></div>
          <div className="flex justify-between gap-4"><dt className="text-slate-600">Still owed</dt><dd className="font-semibold text-slate-900">{formatRupees(recorded.balance)}</dd></div>
        </dl>
      </Modal>
    );
  }

  const facts = [
    ['Billing month', invoice.month],
    ['Invoice total', formatRupees(invoice.amount)],
    ...(invoice.amount_paid > 0 ? [['Already paid', formatRupees(invoice.amount_paid)]] : []),
    ['Still owed', formatRupees(invoice.balance)],
  ];

  return (
    <Modal
      title="Record Payment"
      description={`${invoice.student_name} (${invoice.challan_number})`}
      busy={saving}
      onClose={onClose}
      footer={(
        <>
          <Button variant="ghost" onClick={onClose} disabled={saving}>Cancel</Button>
          <Button type="submit" form={PAYMENT_FORM_ID} variant="success" disabled={saving}>{saving ? 'Saving…' : 'Confirm Payment'}</Button>
        </>
      )}
    >
      <ErrorNotice>{error}</ErrorNotice>
      <dl className="space-y-1 rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm">
        {facts.map(([label, value]) => (
          <div key={label} className="flex justify-between gap-4">
            <dt className="text-slate-600">{label}</dt>
            <dd className="font-semibold text-slate-900">{value}</dd>
          </div>
        ))}
      </dl>

      {historyError && <p className="text-sm text-rose-800">{historyError}</p>}
      {payments.length > 0 && (
        <div>
          <p className="mb-1 text-sm font-semibold text-slate-700">Earlier payments</p>
          <PaymentList payments={payments} />
        </div>
      )}

      <form id={PAYMENT_FORM_ID} onSubmit={handleSubmit} className="space-y-4" noValidate>
        <TextField
          label="Amount received (Rs.)"
          type="number"
          min="1"
          max={invoice.balance}
          step="any"
          hint="Enter less than the full amount to record part payment."
          value={amount}
          onChange={(event) => setAmount(event.target.value)}
        />
        <fieldset>
          <legend className="mb-1 text-sm font-semibold text-slate-700">Paid by</legend>
          <div className="grid grid-cols-3 gap-2">
            {PAYMENT_MODES.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                type="button"
                aria-pressed={mode === id}
                onClick={() => setMode(id)}
                className={`flex min-h-14 flex-col items-center justify-center gap-1 rounded-xl border text-sm font-semibold transition-colors ${
                  mode === id ? 'border-brand-600 bg-brand-50 text-brand-800' : 'border-slate-300 text-slate-700 hover:bg-slate-50'
                }`}
              >
                <Icon className="h-4 w-4" aria-hidden="true" />
                <span>{label}</span>
              </button>
            ))}
          </div>
        </fieldset>
      </form>
    </Modal>
  );
}

export function PaymentHistoryDialog({ invoice, onClose }) {
  const { payments, loading, error, retry } = usePayments(invoice, true);

  return (
    <Modal
      title="Payments"
      description={`${invoice.student_name || ''} ${invoice.month} (${invoice.challan_number})`.trim()}
      onClose={onClose}
      footer={<Button variant="secondary" onClick={onClose}>Close</Button>}
    >
      {loading && <LoadingState label="Loading payments…" />}
      {!loading && error && <ErrorState message={error} onRetry={retry} />}
      {!loading && !error && payments.length === 0 && <EmptyState title="No payments yet" />}
      {!loading && !error && payments.length > 0 && <PaymentList payments={payments} />}
    </Modal>
  );
}
