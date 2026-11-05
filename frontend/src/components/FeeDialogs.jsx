import React, { useEffect, useState } from 'react';
import { Banknote, Building2, CreditCard } from 'lucide-react';
import { api } from '../api/client';
import { apiErrorMessage } from '../lib/errors';
import {
  challanFormError,
  defaultDueDate,
  formatRupees,
  monthLabel,
  monthPickerValue,
  paymentAmountError,
} from '../lib/fees';
import StudentPicker from './StudentPicker';
import Button from './ui/Button';
import { TextField } from './ui/Field';
import Modal from './ui/Modal';
import { ErrorNotice } from './ui/States';

const DEFAULT_FEE_AMOUNT = 4000;
const CHALLAN_FORM_ID = 'challan-form';
const PAYMENT_FORM_ID = 'payment-form';
const PAYMENT_MODES = [
  { id: 'cash', label: 'Cash', icon: Banknote },
  { id: 'bank', label: 'Bank', icon: Building2 },
  { id: 'online', label: 'Online', icon: CreditCard },
];

export function IssueChallanDialog({ onClose, onIssued }) {
  const [student, setStudent] = useState(null);
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

export function RecordPaymentDialog({ invoice, onClose, onPaid, onFailed }) {
  const [amount, setAmount] = useState(String(invoice.balance));
  const [mode, setMode] = useState('cash');
  const [history, setHistory] = useState([]);
  const [historyError, setHistoryError] = useState('');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!(invoice.amount_paid > 0)) return undefined;
    const controller = new AbortController();
    api.getInvoicePayments(invoice.id, { signal: controller.signal })
      .then((res) => setHistory(res.data))
      .catch((err) => {
        if (err.code !== 'ERR_CANCELED') setHistoryError(apiErrorMessage(err, 'Earlier payments could not be loaded.'));
      });
    return () => controller.abort();
  }, [invoice.id, invoice.amount_paid]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (saving) return;
    const problem = paymentAmountError(amount, invoice.balance);
    setError(problem || '');
    if (problem) return;

    setSaving(true);
    try {
      await api.payInvoice(invoice.id, { amount_paid: parseFloat(amount), payment_mode: mode });
      onPaid(`${formatRupees(parseFloat(amount))} recorded for ${invoice.student_name}.`);
    } catch (err) {
      setError(apiErrorMessage(err, 'The payment could not be recorded. Please try again.'));
      setSaving(false);
      onFailed();
    }
  };

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
      {history.length > 0 && (
        <div className="text-sm">
          <p className="mb-1 font-semibold text-slate-700">Earlier payments</p>
          <ul className="space-y-1 text-slate-700">
            {history.map((payment) => (
              <li key={payment.id} className="flex justify-between gap-4">
                <span className="capitalize">{payment.payment_mode} &bull; {new Date(payment.paid_at).toLocaleDateString()}</span>
                <span className="font-semibold">{formatRupees(payment.amount_paid)}</span>
              </li>
            ))}
          </ul>
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
