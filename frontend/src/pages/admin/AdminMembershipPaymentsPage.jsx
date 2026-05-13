import { Plus, Save } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import {
  Card,
  DataTable,
  ErrorBanner,
  FormField,
  LoadingState,
  PrimaryButton,
  SelectInput,
  StatusBadge,
  TextArea,
  TextInput,
} from "../../components/ui.jsx";
import { apiClient } from "../../api/client.js";
import { useAuth } from "../../context/AuthContext.jsx";
import { buildAgentName, useAdminAgentRecords, useAgent, useAgents } from "../../hooks/useAdminData.js";
import { getFriendlyError, useApiResource } from "../../hooks/useAgentPortalData.js";
import { formatDate, formatMoney } from "../../utils/formatters.js";
import { membershipStatuses, paymentStatuses } from "./adminConstants.js";
import AdminPageShell, { AdminLinkButton } from "./AdminPageShell.jsx";

const blankMembership = {
  membership_type: "Standard",
  setup_fee_amount: "0",
  monthly_fee_amount: "0",
  membership_status: "Payment Pending",
  payment_status: "Not Started",
  payment_method: "",
  last_payment_date: "",
  next_payment_date: "",
  failed_payment_count: 0,
  access_level: "",
  internal_notes: "",
};

const blankPayment = {
  amount: "",
  currency: "GBP",
  payment_type: "Membership",
  payment_status: "Pending",
  payment_date: "",
  due_date: "",
  invoice_url: "",
  notes: "",
};

export default function AdminMembershipPaymentsPage() {
  const { agentId } = useParams();

  if (!agentId) {
    return <MembershipOverview />;
  }

  return <MembershipDetail agentId={agentId} />;
}

function MembershipOverview() {
  const agents = useAgents();
  const memberships = useAdminAgentRecords(agents.data, "membership");

  if (agents.loading || memberships.loading) {
    return (
      <AdminPageShell title="Membership & Payments Admin" description="Review membership and payment status across agents.">
        <LoadingState message="Loading membership records..." />
      </AdminPageShell>
    );
  }

  return (
    <AdminPageShell title="Membership & Payments Admin" description="Review all agent memberships and open a record to update payment status.">
      <div className="space-y-6">
        <ErrorBanner message={agents.error || memberships.error} />

        <Card title="Membership Records">
          <DataTable
            rows={memberships.records}
            emptyMessage="No membership records have been added yet."
            columns={[
              { key: "agent", label: "Agent", render: (row) => <Link className="font-semibold text-sky-700 hover:text-sky-900" to={`/admin/agents/${row.agent.id}/membership`}>{buildAgentName(row.agent)}</Link> },
              { key: "membership_type", label: "Type" },
              { key: "membership_status", label: "Membership", render: (row) => <StatusBadge status={row.membership_status} /> },
              { key: "payment_status", label: "Payment", render: (row) => <StatusBadge status={row.payment_status} /> },
              { key: "monthly_fee_amount", label: "Monthly", render: (row) => formatMoney(row.monthly_fee_amount) },
              { key: "next_payment_date", label: "Next payment", render: (row) => formatDate(row.next_payment_date) },
            ]}
          />
        </Card>
      </div>
    </AdminPageShell>
  );
}

function MembershipDetail({ agentId }) {
  const { token } = useAuth();
  const agent = useAgent(agentId);
  const membership = useApiResource(`/agents/${agentId}/membership`, {
    fallbackError: "No membership record exists yet. Saving the form will create one.",
  });
  const payments = useApiResource(`/agents/${agentId}/payments`, {
    initialData: [],
    fallbackError: "We could not load payment records.",
  });
  const [membershipForm, setMembershipForm] = useState(blankMembership);
  const [paymentForm, setPaymentForm] = useState(blankPayment);
  const [saving, setSaving] = useState(false);
  const [addingPayment, setAddingPayment] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (membership.data) {
      setMembershipForm({
        membership_type: membership.data.membership_type || "Standard",
        setup_fee_amount: String(membership.data.setup_fee_amount ?? "0"),
        monthly_fee_amount: String(membership.data.monthly_fee_amount ?? "0"),
        membership_status: membership.data.membership_status || "Payment Pending",
        payment_status: membership.data.payment_status || "Not Started",
        payment_method: membership.data.payment_method || "",
        last_payment_date: membership.data.last_payment_date || "",
        next_payment_date: membership.data.next_payment_date || "",
        failed_payment_count: membership.data.failed_payment_count || 0,
        access_level: membership.data.access_level || "",
        internal_notes: membership.data.internal_notes || "",
      });
    }
  }, [membership.data]);

  function updateMembership(field, value) {
    setMembershipForm((current) => ({ ...current, [field]: value }));
  }

  function updatePayment(field, value) {
    setPaymentForm((current) => ({ ...current, [field]: value }));
  }

  async function saveMembership(event) {
    event.preventDefault();
    setSaving(true);
    setError("");
    setMessage("");

    try {
      await apiClient.put(
        `/agents/${agentId}/membership`,
        {
          ...membershipForm,
          setup_fee_amount: membershipForm.setup_fee_amount || "0",
          monthly_fee_amount: membershipForm.monthly_fee_amount || "0",
          last_payment_date: membershipForm.last_payment_date || null,
          next_payment_date: membershipForm.next_payment_date || null,
          failed_payment_count: Number(membershipForm.failed_payment_count || 0),
        },
        token,
      );
      await membership.reload();
      setMessage("Membership saved.");
    } catch (err) {
      setError(getFriendlyError(err, "We could not save this membership."));
    } finally {
      setSaving(false);
    }
  }

  async function addPayment(event) {
    event.preventDefault();
    setAddingPayment(true);
    setError("");
    setMessage("");

    try {
      await apiClient.post(
        `/agents/${agentId}/payments`,
        {
          ...paymentForm,
          payment_date: paymentForm.payment_date || null,
          due_date: paymentForm.due_date || null,
          amount: paymentForm.amount || "0",
        },
        token,
      );
      setPaymentForm(blankPayment);
      await payments.reload();
      setMessage("Payment record added.");
    } catch (err) {
      setError(getFriendlyError(err, "We could not add this payment."));
    } finally {
      setAddingPayment(false);
    }
  }

  const paymentRows = useMemo(() => payments.data || [], [payments.data]);

  if (agent.loading || payments.loading) {
    return (
      <AdminPageShell title="Membership & Payments Admin" description="Loading selected agent payment records.">
        <LoadingState message="Loading membership detail..." />
      </AdminPageShell>
    );
  }

  return (
    <AdminPageShell
      title="Membership & Payments Admin"
      description={agent.data ? `Manage membership and payment tracking for ${buildAgentName(agent.data)}.` : "Manage membership and payment tracking."}
      actions={<AdminLinkButton to="/admin/membership">All memberships</AdminLinkButton>}
    >
      <div className="space-y-6">
        <ErrorBanner message={agent.error || error} />
        {membership.error ? <ErrorBanner message={membership.error} /> : null}
        {message ? <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm font-medium text-emerald-700">{message}</div> : null}

        <form onSubmit={saveMembership}>
          <Card title="Membership Status">
            <div className="grid gap-4 md:grid-cols-3">
              <FormField label="Membership type">
                <TextInput value={membershipForm.membership_type} onChange={(event) => updateMembership("membership_type", event.target.value)} />
              </FormField>
              <FormField label="Membership status">
                <SelectInput value={membershipForm.membership_status} onChange={(event) => updateMembership("membership_status", event.target.value)}>
                  {membershipStatuses.map((status) => <option key={status} value={status}>{status}</option>)}
                </SelectInput>
              </FormField>
              <FormField label="Payment status">
                <SelectInput value={membershipForm.payment_status} onChange={(event) => updateMembership("payment_status", event.target.value)}>
                  {paymentStatuses.map((status) => <option key={status} value={status}>{status}</option>)}
                </SelectInput>
              </FormField>
              <FormField label="Setup fee">
                <TextInput type="number" min="0" step="0.01" value={membershipForm.setup_fee_amount} onChange={(event) => updateMembership("setup_fee_amount", event.target.value)} />
              </FormField>
              <FormField label="Monthly fee">
                <TextInput type="number" min="0" step="0.01" value={membershipForm.monthly_fee_amount} onChange={(event) => updateMembership("monthly_fee_amount", event.target.value)} />
              </FormField>
              <FormField label="Payment method">
                <TextInput value={membershipForm.payment_method} onChange={(event) => updateMembership("payment_method", event.target.value)} />
              </FormField>
              <FormField label="Last payment date">
                <TextInput type="date" value={membershipForm.last_payment_date} onChange={(event) => updateMembership("last_payment_date", event.target.value)} />
              </FormField>
              <FormField label="Next payment date">
                <TextInput type="date" value={membershipForm.next_payment_date} onChange={(event) => updateMembership("next_payment_date", event.target.value)} />
              </FormField>
              <FormField label="Failed payment count">
                <TextInput type="number" min="0" value={membershipForm.failed_payment_count} onChange={(event) => updateMembership("failed_payment_count", event.target.value)} />
              </FormField>
              <FormField label="Access level">
                <TextInput value={membershipForm.access_level} onChange={(event) => updateMembership("access_level", event.target.value)} />
              </FormField>
              <div className="md:col-span-2">
                <FormField label="Internal notes">
                  <TextArea value={membershipForm.internal_notes} onChange={(event) => updateMembership("internal_notes", event.target.value)} />
                </FormField>
              </div>
            </div>
            <div className="mt-4">
              <PrimaryButton type="submit" icon={Save} disabled={saving}>{saving ? "Saving..." : "Save membership"}</PrimaryButton>
            </div>
          </Card>
        </form>

        <form onSubmit={addPayment}>
          <Card title="Add Payment Record" description="This tracks a payment record. It does not charge real money yet.">
            <div className="grid gap-4 md:grid-cols-3">
              <FormField label="Amount">
                <TextInput required type="number" min="0" step="0.01" value={paymentForm.amount} onChange={(event) => updatePayment("amount", event.target.value)} />
              </FormField>
              <FormField label="Currency">
                <TextInput value={paymentForm.currency} onChange={(event) => updatePayment("currency", event.target.value.toUpperCase())} />
              </FormField>
              <FormField label="Payment type">
                <TextInput value={paymentForm.payment_type} onChange={(event) => updatePayment("payment_type", event.target.value)} />
              </FormField>
              <FormField label="Payment status">
                <SelectInput value={paymentForm.payment_status} onChange={(event) => updatePayment("payment_status", event.target.value)}>
                  {paymentStatuses.map((status) => <option key={status} value={status}>{status}</option>)}
                </SelectInput>
              </FormField>
              <FormField label="Payment date">
                <TextInput type="date" value={paymentForm.payment_date} onChange={(event) => updatePayment("payment_date", event.target.value)} />
              </FormField>
              <FormField label="Due date">
                <TextInput type="date" value={paymentForm.due_date} onChange={(event) => updatePayment("due_date", event.target.value)} />
              </FormField>
              <FormField label="Invoice URL">
                <TextInput value={paymentForm.invoice_url} onChange={(event) => updatePayment("invoice_url", event.target.value)} />
              </FormField>
              <div className="md:col-span-2">
                <FormField label="Notes">
                  <TextArea value={paymentForm.notes} onChange={(event) => updatePayment("notes", event.target.value)} />
                </FormField>
              </div>
            </div>
            <div className="mt-4">
              <PrimaryButton type="submit" icon={Plus} disabled={addingPayment}>{addingPayment ? "Adding..." : "Add payment"}</PrimaryButton>
            </div>
          </Card>
        </form>

        <Card title="Payment Records">
          <DataTable
            rows={paymentRows}
            emptyMessage="No payment records have been added yet."
            columns={[
              { key: "payment_type", label: "Type" },
              { key: "amount", label: "Amount", render: (row) => formatMoney(row.amount, row.currency) },
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
      </div>
    </AdminPageShell>
  );
}
