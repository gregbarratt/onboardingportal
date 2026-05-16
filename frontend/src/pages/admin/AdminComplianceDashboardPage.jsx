import { Download, Eye, Pencil, Plus, Trash2, X } from "lucide-react";
import { useState } from "react";

import { Card, DataTable, ErrorBanner, FormField, LoadingState, PrimaryButton, SecondaryButton, SelectInput, StatCard, StatusBadge, TextArea, TextInput } from "../../components/ui.jsx";
import { API_BASE_URL, apiClient } from "../../api/client.js";
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
  const [selectedPolicy, setSelectedPolicy] = useState(null);
  const [editingPolicy, setEditingPolicy] = useState(null);
  const [editForm, setEditForm] = useState(blankPolicy);
  const [updating, setUpdating] = useState(false);
  const [removingId, setRemovingId] = useState(null);
  const [downloadingId, setDownloadingId] = useState(null);

  function update(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function updateEdit(field, value) {
    setEditForm((current) => ({ ...current, [field]: value }));
  }

  function startEditPolicy(policy) {
    setEditingPolicy(policy);
    setEditForm({
      title: policy.title || "",
      policy_type: policy.policy_type || "Compliance Policy",
      content: policy.content || "",
      version: policy.version || "1.0",
      requires_acceptance: Boolean(policy.requires_acceptance),
      published_status: policy.published_status || "Published",
    });
    setError("");
    setMessage("");
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

  async function savePolicy(event) {
    event.preventDefault();
    if (!editingPolicy) return;

    setUpdating(true);
    setError("");
    setMessage("");

    try {
      await apiClient.put(`/compliance/policies/${editingPolicy.id}`, editForm, token);
      setEditingPolicy(null);
      await policies.reload();
      await dashboard.reload();
      setMessage("Compliance policy updated.");
    } catch (err) {
      setError(getFriendlyError(err, "We could not update this compliance policy."));
    } finally {
      setUpdating(false);
    }
  }

  async function removePolicy(policy) {
    const confirmed = window.confirm(
      "Remove this policy? If agents have already accepted it, the portal will archive it instead of deleting the signed history.",
    );
    if (!confirmed) return;

    setRemovingId(policy.id);
    setError("");
    setMessage("");

    try {
      const result = await apiClient.delete(`/compliance/policies/${policy.id}`, token);
      await policies.reload();
      await dashboard.reload();
      setMessage(result.message || "Policy removed.");
    } catch (err) {
      setError(getFriendlyError(err, "We could not remove this compliance policy."));
    } finally {
      setRemovingId(null);
    }
  }

  async function downloadAcceptanceReceipt(acceptance) {
    setDownloadingId(acceptance.id);
    setError("");

    try {
      const response = await fetch(`${API_BASE_URL}/policy-acceptances/${acceptance.id}/receipt.pdf`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        throw new Error("The PDF receipt could not be exported.");
      }
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `policy-acceptance-${acceptance.agent_name || acceptance.agent_id}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(getFriendlyError(err, "We could not export this policy acceptance PDF."));
    } finally {
      setDownloadingId(null);
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

        <Card title="Recent Policy Acceptances" description="Signed policy records include the date, user, IP address, and an exportable PDF receipt.">
          <DataTable
            rows={data?.recent_policy_acceptances || []}
            emptyMessage="No policy acceptances have been recorded yet."
            columns={[
              { key: "agent_name", label: "Agent", render: (row) => row.agent_name || `Agent ${row.agent_id}` },
              { key: "policy", label: "Policy", render: (row) => row.policy?.title || "Not shown" },
              { key: "policy_version", label: "Version" },
              { key: "accepted_date", label: "Accepted", render: (row) => formatDateTime(row.accepted_date) },
              { key: "ip_address", label: "IP address", render: (row) => row.ip_address || "Not recorded" },
              {
                key: "export",
                label: "Export",
                render: (row) => (
                  <SecondaryButton type="button" icon={Download} disabled={downloadingId === row.id} onClick={() => downloadAcceptanceReceipt(row)}>
                    {downloadingId === row.id ? "Exporting..." : "PDF"}
                  </SecondaryButton>
                ),
              },
            ]}
          />
        </Card>

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
              {
                key: "action",
                label: "Action",
                render: (row) => (
                  <div className="flex flex-wrap gap-2">
                    <SecondaryButton type="button" icon={Eye} onClick={() => setSelectedPolicy(row)}>
                      Read
                    </SecondaryButton>
                    <SecondaryButton type="button" icon={Pencil} onClick={() => startEditPolicy(row)}>
                      Edit
                    </SecondaryButton>
                    <SecondaryButton type="button" icon={Trash2} disabled={removingId === row.id} onClick={() => removePolicy(row)}>
                      {removingId === row.id ? "Removing..." : "Remove"}
                    </SecondaryButton>
                  </div>
                ),
              },
            ]}
          />
        </Card>

        {selectedPolicy ? (
          <PolicyReadModal policy={selectedPolicy} onClose={() => setSelectedPolicy(null)} />
        ) : null}

        {editingPolicy ? (
          <PolicyEditModal
            policy={editingPolicy}
            form={editForm}
            updating={updating}
            onChange={updateEdit}
            onSubmit={savePolicy}
            onClose={() => setEditingPolicy(null)}
          />
        ) : null}
      </div>
    </AdminPageShell>
  );
}

function PolicyEditModal({ policy, form, updating, onChange, onSubmit, onClose }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4">
      <div className="flex max-h-[90vh] w-full max-w-5xl flex-col rounded-lg bg-white shadow-xl">
        <div className="flex items-start justify-between gap-4 border-b border-slate-200 p-5">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-sky-700">Edit compliance policy</p>
            <h2 className="mt-1 text-xl font-semibold text-slate-950">{policy.title}</h2>
            <p className="mt-1 text-sm text-slate-600">Changes affect what agents see from now on.</p>
          </div>
          <button type="button" className="rounded-lg p-2 text-slate-500 hover:bg-slate-100" onClick={onClose} aria-label="Close edit form">
            <X className="h-5 w-5" aria-hidden="true" />
          </button>
        </div>
        <form onSubmit={onSubmit} className="overflow-y-auto p-5">
          <div className="grid gap-4 md:grid-cols-2">
            <FormField label="Title">
              <TextInput required value={form.title} onChange={(event) => onChange("title", event.target.value)} />
            </FormField>
            <FormField label="Policy type">
              <SelectInput value={form.policy_type} onChange={(event) => onChange("policy_type", event.target.value)}>
                {compliancePolicyTypes.map((type) => <option key={type} value={type}>{type}</option>)}
              </SelectInput>
            </FormField>
            <FormField label="Version">
              <TextInput required value={form.version} onChange={(event) => onChange("version", event.target.value)} />
            </FormField>
            <FormField label="Published status">
              <SelectInput value={form.published_status} onChange={(event) => onChange("published_status", event.target.value)}>
                {compliancePolicyStatuses.map((status) => <option key={status} value={status}>{status}</option>)}
              </SelectInput>
            </FormField>
            <div className="md:col-span-2">
              <FormField label="Policy content">
                <TextArea required value={form.content} onChange={(event) => onChange("content", event.target.value)} className="min-h-64" />
              </FormField>
            </div>
            <div className="md:col-span-2 flex items-center gap-2">
              <input type="checkbox" checked={form.requires_acceptance} onChange={(event) => onChange("requires_acceptance", event.target.checked)} />
              <span className="text-sm font-medium text-slate-700">Requires agent acceptance</span>
            </div>
          </div>
          <div className="mt-5 flex flex-wrap justify-end gap-3 border-t border-slate-200 pt-5">
            <SecondaryButton type="button" icon={X} onClick={onClose}>
              Cancel
            </SecondaryButton>
            <PrimaryButton type="submit" icon={Pencil} disabled={updating}>
              {updating ? "Saving..." : "Save policy"}
            </PrimaryButton>
          </div>
        </form>
      </div>
    </div>
  );
}

function PolicyReadModal({ policy, onClose }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4">
      <div className="flex max-h-[90vh] w-full max-w-4xl flex-col rounded-lg bg-white shadow-xl">
        <div className="flex items-start justify-between gap-4 border-b border-slate-200 p-5">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-sky-700">Compliance policy</p>
            <h2 className="mt-1 text-xl font-semibold text-slate-950">{policy.title}</h2>
            <p className="mt-1 text-sm text-slate-600">
              {policy.policy_type} | Version {policy.version}
            </p>
          </div>
          <button type="button" className="rounded-lg p-2 text-slate-500 hover:bg-slate-100" onClick={onClose} aria-label="Close policy">
            <X className="h-5 w-5" aria-hidden="true" />
          </button>
        </div>
        <div className="overflow-y-auto p-5">
          <div className="whitespace-pre-wrap rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm leading-6 text-slate-800">
            {policy.content}
          </div>
        </div>
        <div className="flex justify-end border-t border-slate-200 p-5">
          <SecondaryButton type="button" icon={X} onClick={onClose}>
            Close
          </SecondaryButton>
        </div>
      </div>
    </div>
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
