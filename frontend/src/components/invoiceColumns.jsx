import React from 'react';
import { Link } from 'react-router-dom';
import { CheckCircle2, Clock, Download } from 'lucide-react';
import { api } from '../api/client';
import { formatRupees } from '../lib/fees';
import PdfButton from './PdfButton';
import Button from './ui/Button';
import { Badge } from './ui/Page';

function StatusBadge({ status }) {
  if (status === 'paid') return <Badge tone="good"><CheckCircle2 className="h-3 w-3" aria-hidden="true" /> Paid</Badge>;
  if (status === 'partial') return <Badge tone="warn"><Clock className="h-3 w-3" aria-hidden="true" /> Part Paid</Badge>;
  return <Badge tone="bad"><Clock className="h-3 w-3" aria-hidden="true" /> Pending</Badge>;
}

const studentColumn = {
  header: 'Student',
  mobile: 'title',
  render: (invoice) => (
    <div>
      <Link to={`/students/${invoice.student_id}`} className="inline-flex min-h-11 items-center font-bold text-slate-900 underline-offset-2 hover:underline">{invoice.student_name}</Link>
      {invoice.student_archived && <span className="ml-1.5"><Badge>Archived</Badge></span>}
      <div className="text-xs text-slate-600">Roll #{invoice.roll_number} &bull; {invoice.grade}-{invoice.section}</div>
    </div>
  ),
};

/** The columns of a list of challans, used on the Fees page and on a student's profile. */
export function invoiceColumns({ showStudent, onPay, onHistory }) {
  const monthColumn = showStudent
    ? { header: 'Month', render: (invoice) => invoice.month }
    : { header: 'Month', mobile: 'title', render: (invoice) => <span className="font-bold text-slate-900">{invoice.month}</span> };

  return [
    ...(showStudent ? [studentColumn] : []),
    { header: 'Challan No', render: (invoice) => <span className="font-mono text-xs font-semibold">{invoice.challan_number}</span> },
    monthColumn,
    { header: 'Amount', render: (invoice) => (
      <div>
        <div className="font-bold text-slate-900">{formatRupees(invoice.amount)}</div>
        {invoice.amount_paid > 0 && invoice.balance > 0 && (
          <div className="text-xs text-slate-600">Paid {formatRupees(invoice.amount_paid)} &bull; <span className="font-semibold text-rose-800">Owes {formatRupees(invoice.balance)}</span></div>
        )}
      </div>
    ) },
    { header: 'Due Date', render: (invoice) => (
      <div>
        <div>{invoice.due_date}</div>
        {invoice.is_overdue && <div className="text-xs font-bold text-rose-800">Overdue</div>}
      </div>
    ) },
    { header: 'Status', render: (invoice) => <StatusBadge status={invoice.status} /> },
    { header: 'Actions', align: 'right', mobile: 'actions', render: (invoice) => (
      <div className="flex flex-wrap items-center gap-2 md:justify-end">
        {invoice.status !== 'paid' && <Button variant="success" onClick={() => onPay(invoice)}>Record Payment</Button>}
        {invoice.amount_paid > 0 && <Button variant="secondary" onClick={() => onHistory(invoice)}>Payments</Button>}
        <PdfButton fetchPdf={() => api.getChallanPdf(invoice.id)} title={`Challan ${invoice.challan_number}`}>
          <Download className="h-4 w-4" aria-hidden="true" />
          <span>Challan</span>
        </PdfButton>
      </div>
    ) },
  ];
}
