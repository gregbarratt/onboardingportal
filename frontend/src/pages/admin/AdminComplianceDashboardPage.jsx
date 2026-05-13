import { Plus } from "lucide-react";
import { useState } from "react";

import { Card, DataTable, ErrorBanner, FormField, LoadingState, PrimaryButton, SelectInput, StatCard, StatusBadge, TextArea, TextInput } from "../../components/ui.jsx";
import { apiClient } from "../../api/client.js";
import { useAuth } from "../../context/AuthContext.jsx";
import { getFriendlyError, useApiResource } from "../../hooks/useAgentPortalData.js";
import { formatDateTime } from "../../utils/formatters.js";
import { compliancePolicyStatuses, compliancePolicyTypes } from "./adminConstants.js";
import AdminPageShell from "./AdminPageShell.jsx";

const blankPolicy = {
  title: "",
  policy_type: "Compliance Policy",
  content: "",
  version: "1.0",
  requires_acceptance: true,
  published_status: "Published",
};

export default function AdminComplianceDashboardPage() {
  const { token } = useAuth();
  const dashboard = useApiResource("/admin/compliance-dashboard", {
    fallbackError: "We could not load the compliance dashboard.",
  });
  const policies = useApiResource("/compliance/policies", {
    initialData: [],
    fallbackError: "We could not load compliance policies.",
  });
  const [form, setForm] = useState(blankPolicy);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  function update(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function createPolicy(event) {
    event.preventDefault();
    setSaving(true);
    setError("");
    setMessage("");

    try {
      await apiClient.post("/compliance/policies", form, token);
      setForm(blankPolicy);
      await policies.reload();
      await dashboard.reload();
      setMessage("Compliance policy created.");
    } catch (err) {
      setError(getFriendlyError(err, "We could not create this compliance policy."));
    } finally {
      setSaving(false);
    }
  }

  if (dashboard.loading || policies.loading) {
    return (
      <AdminPageShell title="Compliance Dashboard" description="Loading compliance dashboard.">
        <LoadingState message="Loading compliance dashboard..." />
      </AdminPageShell>
    );
  }

  const data = dashboard.data;

  return (
    <AdminPageShell title="Compliance Dashboard" description="Monitor missing documents, compliance holds, expired training, and policy acceptance.">
      <div className="space-y-6">
        <ErrorBanner message={dashboard.error || policies.error || error} />
        {message ? <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm font-medium text-emerald-700">{message}</div> : null}

        {data ? (
          <div className="grid gap-4 md:grid-cols-4">
            <StatCard label="Total agents" value={data.total_agents} />
            <StatCard label="Compliance hold" value={data.agents_on_compliance_hold} />
            <StatCard label="Documents awaiting review" value={data.documents_awaiting_review} />
            <StatCard label="Policy acceptances" value={data.policy_acceptance_count} />
          </div>
        ) : null}

        <div className="grid gap-6 xl:grid-cols-2">
          <IssueTable title="Missing Documents" rows={data?.missing_document_agents || []} />
          <IssueTable title="Expired Compliance Training" rows={data?.expired_compliance_training_agents || []} />
        </div>

        <Card title="Create Compliance Policy">
          <form onSubmit={createPolicy} className="grid gap-4 md:grid-cols-2">
            <FormField label="Title">
              <TextInput required value={form.title} onChange={(event) => update("title", event.target.value)} />
            </FormField>
            <FormField label="Policy type">
              <SelectInput value={form.policy_type} onChange={(event) => update("policy_type", event.target.value)}>
                {compliancePolicyTypes.map((type) => <option key={type} value={type}>{type}</option>)}
              </SelectInput>
            </FormField>
            <FormField label="Version">
              <TextInput value={form.version} onChange={(event) => update("version", event.target.value)} />
            </FormField>
            <FormField label="Published status">
              <SelectInput value={form.published_status} onChange={(event) => update("published_status", event.target.value)}>
                {compliancePolicyStatuses.map((status) => <option key={status} value={status}>{status}</option>)}
              </SelectInput>
            </FormField>
            <div className="md:col-span-2">
              <FormField label="Policy content">
                <TextArea required value={form.content} onChange={(event) => update("content", event.target.value)} />
              </FormField>
            </div>
            <div className="md:col-span-2 flex items-center gap-2">
              <input type="checkbox" checked={form.requires_acceptance} onChange={(event) => update("requires_acceptance", event.target.checked)} />
              <span className="text-sm font-medium text-slate-700">Requires agent acceptance</span>
            </div>
            <div className="md:col-span-2">
              <PrimaryButton type="submit" icon={Plus} disabled={saving}>{saving ? "Creating..." : "Create policy"}</PrimaryButton>
            </div>
          </form>
        </Card>

        <Card title="Policies">
          <DataTable
            rows={policies.data || []}
            emptyMessage="No compliance policies have been created yet."
            columns={[
              { key: "title", label: "Policy" },
              { key: "policy_type", label: "Type" },
              { key: "version", label: "Version" },
              { key: "published_status", label: "Status", render: (row) => <StatusBadge status={row.published_status} /> },
              { key: "created_at", label: "Created", render: (row) => formatDateTime(row.created_at) },
            ]}
          />
        </Card>
      </div>
    </AdminPageShell>
  );
}

function IssueTable({ title, rows }) {
  return (
    <Card title={title}>
      <DataTable
        rows={rows}
        emptyMessage="No issues in this category."
        columns={[
          { key: "agent_name", label: "Agent" },
          { key: "status", label: "Status", render: (row) => <StatusBadge status={row.status} /> },
          { key: "issues", label: "Issues", render: (row) => row.issues?.join(", ") || "None" },
        ]}
      />
    </Card>
  );
}
