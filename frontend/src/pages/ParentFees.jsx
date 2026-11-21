import React from 'react';
import { Download, Info } from 'lucide-react';
import { api } from '../api/client';
import DataTable from '../components/DataTable';
import { StatusBadge } from '../components/invoiceColumns';
import ParentChildPage from '../components/ParentChildPage';
import PdfButton from '../components/PdfButton';
import StatCard from '../components/StatCard';
import { Card } from '../components/ui/Page';
import { ErrorState, LoadingState } from '../components/ui/States';
import { formatDate } from '../lib/activity';
import { formatRupees } from '../lib/fees';
import { paymentHistory, paymentModeLabel } from '../lib/parent';
import { useLoad } from '../lib/useLoad';

function FeesBody({ child }) {
  const { data, loading, error, reload } = useLoad(
    (options) => api.getParentChildFees(child.id, options),
    String(child.id),
    'Could not load the fees. Please try again.',
  );

  if (error && !data) return <ErrorState message={error} onRetry={reload} />;
  if (!data) return <LoadingState label="Loading fees…" />;

  const { totals } = data;

  const invoiceColumns = [
    { header: 'Month', mobile: 'title', render: (invoice) => <span className="font-bold text-slate-900">{invoice.month}</span> },
    { header: 'Challan No', render: (invoice) => <span className="font-mono text-xs font-semibold">{invoice.challan_number}</span> },
    {
      header: 'Amount',
      render: (invoice) => (
        <div>
          <div className="font-bold text-slate-900">{formatRupees(invoice.amount)}</div>
          {invoice.amount_paid > 0 && <div className="text-xs text-slate-600">Paid {formatRupees(invoice.amount_paid)}</div>}
        </div>
      ),
    },
    {
      header: 'To pay',
      render: (invoice) => (
        <span className={invoice.balance > 0 ? 'font-bold text-rose-800' : 'text-slate-700'}>{formatRupees(invoice.balance)}</span>
      ),
    },
    {
      header: 'Due date',
      render: (invoice) => (
        <div>
          <div>{invoice.due_date}</div>
          {invoice.is_overdue && <div className="text-xs font-bold text-rose-800">Overdue</div>}
        </div>
      ),
    },
    { header: 'Status', render: (invoice) => <StatusBadge status={invoice.status} /> },
    {
      header: 'Challan',
      align: 'right',
      mobile: 'actions',
      render: (invoice) => (
        <PdfButton fetchPdf={() => api.getParentChallanPdf(child.id, invoice.id)} title={`Challan ${invoice.challan_number}`}>
          <Download className="h-4 w-4" aria-hidden="true" />
          <span>Challan<span className="sr-only"> {invoice.month}</span></span>
        </PdfButton>
      ),
    },
  ];

  const paymentColumns = [
    { header: 'Receipt No', mobile: 'title', render: (payment) => <span className="font-mono text-xs font-semibold">{payment.receipt_number}</span> },
    { header: 'For', render: (payment) => payment.month },
    { header: 'Received on', render: (payment) => formatDate(payment.paid_at) },
    { header: 'Paid by', render: (payment) => paymentModeLabel(payment.payment_mode) },
    { header: 'Amount', render: (payment) => <span className="font-bold text-slate-900">{formatRupees(payment.amount_paid)}</span> },
    {
      header: 'Receipt',
      align: 'right',
      mobile: 'actions',
      render: (payment) => (
        <PdfButton fetchPdf={() => api.getParentReceiptPdf(child.id, payment.id)} title={`Receipt ${payment.receipt_number}`}>
          <Download className="h-4 w-4" aria-hidden="true" />
          <span>Receipt<span className="sr-only"> {payment.receipt_number}</span></span>
        </PdfButton>
      ),
    },
  ];

  return (
    <>
      <section aria-label="Fee summary" className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard title="Total billed" value={formatRupees(totals.invoiced)} subtitle={`${totals.invoice_count} ${totals.invoice_count === 1 ? 'challan' : 'challans'}`} />
        <StatCard title="Paid" value={formatRupees(totals.collected)} color="green" />
        <StatCard title="To pay" value={formatRupees(totals.outstanding)} color={totals.outstanding > 0 ? 'amber' : 'green'} />
        <StatCard title="Overdue" value={formatRupees(totals.overdue)} color={totals.overdue > 0 ? 'red' : 'green'} />
      </section>
      <p className="flex items-start gap-2 text-xs text-slate-600">
        <Info className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
        <span>Online payment is not available. Print the challan and pay at the school office or bank, and keep the receipt.</span>
      </p>

      <section aria-labelledby="invoices-heading" className="space-y-2">
        <h2 id="invoices-heading" className="text-base font-bold text-slate-900">Fee challans</h2>
        <Card>
          <DataTable
            columns={invoiceColumns}
            rows={data.invoices}
            loading={loading}
            error={error}
            onRetry={reload}
            loadingLabel="Loading fees…"
            emptyState={{ title: 'No fee challans yet', message: 'Challans appear here when the school issues them.' }}
          />
        </Card>
      </section>

      <section aria-labelledby="payments-heading" className="space-y-2">
        <h2 id="payments-heading" className="text-base font-bold text-slate-900">Payment history</h2>
        <Card>
          <DataTable
            columns={paymentColumns}
            rows={paymentHistory(data.invoices)}
            emptyState={{ title: 'No payments yet', message: 'Payments the school receives will be listed here with their receipts.' }}
          />
        </Card>
      </section>
    </>
  );
}

export default function ParentFees() {
  return (
    <ParentChildPage title="Fees & Payments" subtitle="Challans, balances and payments received by the school.">
      {(child) => <FeesBody key={child.id} child={child} />}
    </ParentChildPage>
  );
}
