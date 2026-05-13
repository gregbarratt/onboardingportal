import { CreditCard, ReceiptText } from "lucide-react";

import { Card, DataTable, ErrorBanner, LoadingState, StatCard, StatusBadge } from "../../components/ui.jsx";
import { useAgentResource } from "../../hooks/useAgentPortalData.js";
import { formatDate, formatMoney } from "../../utils/formatters.js";
import AgentPageShell from "./AgentPageShell.jsx";

export default function MembershipPaymentsPage() {
  return (
    <AgentPageShell
      title="Membership & Payments"
      description="View your membership status, payment setup, and payment records. Admin will manage payment changes."
    >
      {({ profile }) => <MembershipContent profile={profile} />}
    </AgentPageShell>
  );
}

function MembershipContent({ profile }) {
  const membership = useAgentResource(profile, (id) => `/agents/${id}/membership`, {
    fallbackError: "Membership has not been set up for this agent yet.",
  });
  const payments = useAgentResource(profile, (id) => `/agents/${id}/payments`, {
    initialData: [],
  });
  const stripeInvoices = useAgentResource(profile, (id) => `/agents/${id}/stripe/invoices`, {
    enabled: Boolean(membership.data?.stripe_customer_id),
    initialData: [],
    fallbackError: "Stripe invoices could not be loaded.",
  });

  if (membership.loading || payments.loading || stripeInvoices.loading) {
    return <LoadingState message="Loading membership and payments..." />;
  }

  const paymentRows = payments.data || [];
  const invoiceRows = stripeInvoices.data || [];

  return (
    <div className="space-y-6">
      {membership.error ? <ErrorBanner message={membership.error} /> : null}
      {payments.error ? <ErrorBanner message={payments.error} /> : null}
      {stripeInvoices.error ? <ErrorBanner message={stripeInvoices.error} /> : null}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Membership status" value={membership.data?.membership_status || "Not set"} icon={CreditCard} />
        <StatCard label="Payment status" value={membership.data?.payment_status || "Not set"} icon={ReceiptText} />
        <StatCard
          label="Monthly fee"
          value={membership.data ? formatMoney(membership.data.monthly_fee_amount) : "Not set"}
          detail={membership.data?.membership_type || "Membership type not set"}
          icon={CreditCard}
        />
        <StatCard
          label="Next payment"
          value={formatDate(membership.data?.next_payment_date)}
          detail={`${membership.data?.failed_payment_count || 0} failed payments recorded`}
          icon={ReceiptText}
        />
      </div>

      <Card title="Membership Details">
        {membership.data ? (
          <dl className="grid gap-4 text-sm md:grid-cols-3">
            <Detail label="Membership type" value={membership.data.membership_type} />
            <Detail label="Setup fee" value={formatMoney(membership.data.setup_fee_amount)} />
            <Detail label="Payment method" value={membership.data.payment_method} />
            <Detail label="Last payment" value={formatDate(membership.data.last_payment_date)} />
            <Detail label="Access level" value={membership.data.access_level} />
            <div>
              <dt className="text-slate-500">Status</dt>
              <dd className="mt-1">
                <StatusBadge status={membership.data.membership_status} />
              </dd>
            </div>
          </dl>
        ) : (
          <p className="text-sm text-slate-600">The admin team has not added membership details yet.</p>
        )}
      </Card>

      <Card title="Payment Records" description="This is a read-only list for agents. Admin can update payment status.">
        <DataTable
          rows={paymentRows}
          emptyMessage="No payment records have been added yet."
          columns={[
            { key: "payment_type", label: "Type" },
            { key: "amount", label: "Amount", render: (row) => formatMoney(row.amount, row.currency || "GBP") },
            { key: "payment_status", label: "Status", render: (row) => <StatusBadge status={row.payment_status} /> },
            { key: "payment_date", label: "Paid", render: (row) => formatDate(row.payment_date) },
            { key: "due_date", label: "Due", render: (row) => formatDate(row.due_date) },
            {
              key: "invoice_url",
              label: "Invoice",
              render: (row) =>
                row.invoice_url ? (
                  <a className="font-semibold text-sky-700 hover:text-sky-900" href={row.invoice_url} target="_blank" rel="noreferrer">
                    Open invoice
                  </a>
                ) : (
                  "Not set"
                ),
            },
          ]}
        />
      </Card>

      <Card title="Stripe Invoices" description="These are the invoices linked from Stripe for your membership payments.">
        {!membership.data?.stripe_customer_id ? (
          <p className="text-sm text-slate-600">Stripe invoices will appear here once admin links your Stripe customer record.</p>
        ) : (
          <DataTable
            rows={invoiceRows}
            emptyMessage="No Stripe invoices have been found for this customer yet."
            columns={[
              { key: "number", label: "Invoice", render: (row) => row.number || row.stripe_invoice_id },
              { key: "status", label: "Status", render: (row) => <StatusBadge status={row.status} /> },
              { key: "amount_paid", label: "Paid", render: (row) => formatMoney(row.amount_paid, row.currency || "GBP") },
              { key: "amount_due", label: "Due", render: (row) => formatMoney(row.amount_due, row.currency || "GBP") },
              { key: "due_date", label: "Due date", render: (row) => formatDate(row.due_date) },
              {
                key: "hosted_invoice_url",
                label: "Invoice",
                render: (row) =>
                  row.hosted_invoice_url ? (
                    <a className="font-semibold text-sky-700 hover:text-sky-900" href={row.hosted_invoice_url} target="_blank" rel="noreferrer">
                      View invoice
                    </a>
                  ) : (
                    "Not set"
                  ),
              },
              {
                key: "invoice_pdf",
                label: "PDF",
                render: (row) =>
                  row.invoice_pdf ? (
                    <a className="font-semibold text-sky-700 hover:text-sky-900" href={row.invoice_pdf} target="_blank" rel="noreferrer">
                      Download PDF
                    </a>
                  ) : (
                    "Not set"
                  ),
              },
            ]}
          />
        )}
      </Card>
    </div>
  );
}

function Detail({ label, value }) {
  return (
    <div>
      <dt className="text-slate-500">{label}</dt>
      <dd className="mt-1 font-medium text-slate-900">{value || "Not set"}</dd>
    </div>
  );
}
