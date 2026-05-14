import { useState } from "react";
import { CreditCard, ExternalLink, ReceiptText } from "lucide-react";

import { apiClient } from "../../api/client.js";
import { Card, DataTable, ErrorBanner, LoadingState, SecondaryButton, StatCard, StatusBadge } from "../../components/ui.jsx";
import { useAuth } from "../../context/AuthContext.jsx";
import { getFriendlyError, useAgentResource } from "../../hooks/useAgentPortalData.js";
import { formatDate, formatDateTime, formatMoney } from "../../utils/formatters.js";
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
  const { token } = useAuth();
  const [billingLoading, setBillingLoading] = useState(false);
  const [billingError, setBillingError] = useState("");
  const membership = useAgentResource(profile, (id) => `/agents/${id}/membership`, {
    fallbackError: "Membership has not been set up for this agent yet.",
  });
  const payments = useAgentResource(profile, (id) => `/agents/${id}/payments`, {
    initialData: [],
  });

  if (membership.loading || payments.loading) {
    return <LoadingState message="Loading membership and payments..." />;
  }

  const paymentRows = payments.data || [];
  const invoiceRows = paymentRows.filter((row) => row.payment_type === "Stripe Invoice" || row.stripe_payment_id);
  const canManageBilling = Boolean(membership.data?.stripe_customer_id);

  async function openBillingPortal() {
    setBillingLoading(true);
    setBillingError("");

    try {
      const session = await apiClient.post(`/agents/${profile.id}/stripe/billing-portal`, {}, token);
      window.location.assign(session.url);
    } catch (err) {
      setBillingError(getFriendlyError(err, "We could not open Stripe billing management."));
    } finally {
      setBillingLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      {membership.error ? <ErrorBanner message={membership.error} /> : null}
      {payments.error ? <ErrorBanner message={payments.error} /> : null}
      {billingError ? <ErrorBanner message={billingError} /> : null}

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

      <Card
        title="Membership Details"
        actions={
          <SecondaryButton type="button" icon={ExternalLink} disabled={!canManageBilling || billingLoading} onClick={openBillingPortal}>
            {billingLoading ? "Opening Stripe..." : "Manage billing in Stripe"}
          </SecondaryButton>
        }
      >
        {membership.data ? (
          <dl className="grid gap-4 text-sm md:grid-cols-3">
            <Detail label="Membership type" value={membership.data.membership_type} />
            <Detail label="Setup fee" value={formatMoney(membership.data.setup_fee_amount)} />
            <Detail label="Payment method" value={membership.data.payment_method} />
            <Detail label="Recurring payment reference" value={membership.data.stripe_subscription_id} />
            <Detail label="Last payment" value={formatDate(membership.data.last_payment_date)} />
            <Detail label="Stripe last checked" value={formatDateTime(membership.data.stripe_last_synced_at)} />
            <Detail label="Stripe sync status" value={membership.data.stripe_sync_status} />
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
        {!canManageBilling && membership.data ? (
          <p className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
            Billing management will unlock once your Stripe customer record is linked.
          </p>
        ) : null}
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

      <Card title="Stripe Invoices" description="These are saved invoice records from the latest Stripe sync.">
        {!membership.data?.stripe_customer_id ? (
          <p className="text-sm text-slate-600">Stripe invoices will appear here once admin links your Stripe customer record.</p>
        ) : (
          <DataTable
            rows={invoiceRows}
            emptyMessage="No Stripe invoices have been found for this customer yet."
            columns={[
              { key: "stripe_payment_id", label: "Invoice", render: (row) => row.stripe_payment_id || "Stripe invoice" },
              { key: "payment_status", label: "Status", render: (row) => <StatusBadge status={row.payment_status} /> },
              { key: "amount", label: "Amount", render: (row) => formatMoney(row.amount, row.currency || "GBP") },
              { key: "due_date", label: "Due date", render: (row) => formatDate(row.due_date) },
              {
                key: "invoice_url",
                label: "Invoice",
                render: (row) =>
                  row.invoice_url ? (
                    <a className="font-semibold text-sky-700 hover:text-sky-900" href={row.invoice_url} target="_blank" rel="noreferrer">
                      View invoice
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
