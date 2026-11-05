import React, { useEffect, useState } from 'react';
import { CheckCircle2, Clock, Plus, Receipt } from 'lucide-react';
import { api } from '../api/client';
import DataTable from '../components/DataTable';
import { IssueChallanDialog, PaymentHistoryDialog, RecordPaymentDialog } from '../components/FeeDialogs';
import { invoiceColumns } from '../components/invoiceColumns';
import StatCard from '../components/StatCard';
import Button from '../components/ui/Button';
import { SearchInput } from '../components/ui/Field';
import { Card, FilterChips, PageHeader } from '../components/ui/Page';
import { useToast } from '../components/ui/Toast';
import { apiErrorMessage } from '../lib/errors';
import { formatRupees } from '../lib/fees';

const STATUS_FILTERS = [
  { value: 'all', label: 'All' },
  { value: 'pending', label: 'Pending' },
  { value: 'partial', label: 'Part Paid' },
  { value: 'paid', label: 'Paid' },
];
const NOT_LOADED = '–';

export default function Fees() {
  const [invoices, setInvoices] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [search, setSearch] = useState('');
  const [issuing, setIssuing] = useState(false);
  const [payingInvoice, setPayingInvoice] = useState(null);
  const [viewingInvoice, setViewingInvoice] = useState(null);
  const toast = useToast();

  const fetchInvoices = async () => {
    try {
      setLoading(true);
      setLoadError('');
      const params = statusFilter === 'all' ? {} : { status: statusFilter };
      const res = await api.getFees(params);
      setInvoices(res.data);
    } catch (err) {
      setInvoices([]);
      setLoadError(apiErrorMessage(err, 'Could not load fee records. Please try again.'));
    } finally {
      setLoading(false);
    }
  };

  const fetchSummary = async () => {
    try {
      const res = await api.getFeeSummary();
      setSummary(res.data);
    } catch (err) {
      // The cards show a dash rather than a false Rs. 0.
      setSummary(null);
      console.warn('Fee summary did not load:', err);
    }
  };

  const refreshFees = () => {
    fetchInvoices();
    fetchSummary();
  };

  useEffect(() => { refreshFees(); }, [statusFilter]);

  const finish = (message) => {
    setIssuing(false);
    toast.success(message);
    refreshFees();
  };

  const query = search.trim().toLowerCase();
  const shown = invoices.filter((invoice) => (
    !query
    || invoice.challan_number.toLowerCase().includes(query)
    || invoice.student_name.toLowerCase().includes(query)
    || invoice.roll_number.toLowerCase().includes(query)
  ));

  const columns = invoiceColumns({ showStudent: true, onPay: setPayingInvoice, onHistory: setViewingInvoice });

  const isFiltered = Boolean(query) || statusFilter !== 'all';
  const emptyState = isFiltered
    ? { icon: Receipt, title: 'No fee records match', message: 'Try a different search or status.' }
    : {
        icon: Receipt,
        title: 'No challans yet',
        message: 'Issue a challan to start tracking fees.',
        action: <Button onClick={() => setIssuing(true)}><Plus className="h-4 w-4" aria-hidden="true" /><span>Issue Challan</span></Button>,
      };

  return (
    <div className="space-y-5">
      <PageHeader
        title="Fees"
        subtitle="Issue challans, record payments, and see what is still owed."
        actions={<Button onClick={() => setIssuing(true)}><Plus className="h-4 w-4" aria-hidden="true" /><span>Issue Challan</span></Button>}
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard title="Challans issued" value={summary ? summary.invoice_count : NOT_LOADED} icon={Receipt} color="blue" />
        <StatCard title="Collected" value={summary ? formatRupees(summary.collected) : NOT_LOADED} icon={CheckCircle2} color="green" />
        <StatCard
          title="Still owed"
          value={summary ? formatRupees(summary.outstanding) : NOT_LOADED}
          subtitle={summary ? `${formatRupees(summary.overdue)} overdue` : undefined}
          icon={Clock}
          color="red"
        />
      </div>

      <Card className="flex flex-col items-stretch justify-between gap-3 p-4 md:flex-row md:items-center">
        <SearchInput label="Search by challan number, student, or roll number" value={search} onChange={(event) => setSearch(event.target.value)} className="w-full md:w-96" />
        <FilterChips label="Payment status" options={STATUS_FILTERS} value={statusFilter} onChange={setStatusFilter} />
      </Card>

      <Card className="overflow-hidden">
        <DataTable
          columns={columns}
          rows={shown}
          loading={loading}
          error={loadError}
          onRetry={refreshFees}
          loadingLabel="Loading fee records…"
          emptyState={emptyState}
        />
      </Card>

      {issuing && <IssueChallanDialog onClose={() => setIssuing(false)} onIssued={finish} />}
      {payingInvoice && (
        <RecordPaymentDialog invoice={payingInvoice} onClose={() => setPayingInvoice(null)} onRecorded={refreshFees} />
      )}
      {viewingInvoice && <PaymentHistoryDialog invoice={viewingInvoice} onClose={() => setViewingInvoice(null)} />}
    </div>
  );
}
