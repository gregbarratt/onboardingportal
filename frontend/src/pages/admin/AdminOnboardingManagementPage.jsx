import { CheckCircle2, Save } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import {
  Card,
  DataTable,
  ErrorBanner,
  FormField,
  LoadingState,
  PrimaryButton,
  ProgressBar,
  SelectInput,
  StatusBadge,
  TextArea,
  TextInput,
} from "../../components/ui.jsx";
import { apiClient } from "../../api/client.js";
import { useAuth } from "../../context/AuthContext.jsx";
import { buildAgentName, useAgent } from "../../hooks/useAdminData.js";
import { getFriendlyError, useApiResource } from "../../hooks/useAgentPortalData.js";
import { formatDate, percentage } from "../../utils/formatters.js";
import { onboardingStatuses } from "./adminConstants.js";
import AdminPageShell, { AdminLinkButton } from "./AdminPageShell.jsx";

function EvidenceLink({ value }) {
  if (!value) return "Not set";

  return (
    <a className="font-semibold text-sky-700 hover:text-sky-900" href={value} target="_blank" rel="noreferrer">
      Open evidence
    </a>
  );
}

export default function AdminOnboardingManagementPage() {
  const { agentId } = useParams();

  if (!agentId) {
    return <OnboardingOverview />;
  }

  return <OnboardingDetail agentId={agentId} />;
}

function OnboardingOverview() {
  const onboarding = useApiResource("/admin/onboarding-summary", {
    initialData: [],
    fallbackError: "We could not load onboarding summaries.",
  });

  if (onboarding.loading) {
    return (
      <AdminPageShell title="Onboarding Management" description="Review agent checklist progress.">
        <LoadingState message="Loading onboarding summaries..." />
      </AdminPageShell>
    );
  }

  return (
    <AdminPageShell title="Onboarding Management" description="Track checklist progress and open an agent to approve steps.">
      <div className="space-y-6">
        <ErrorBanner message={onboarding.error} />
        <Card title="Agent Checklist Progress">
          <DataTable
            rows={onboarding.data || []}
            emptyMessage="No agents are available yet."
            columns={[
              { key: "agent", label: "Agent", render: (row) => <Link className="font-semibold text-sky-700 hover:text-sky-900" to={`/admin/agents/${row.id}/onboarding`}>{buildAgentName(row)}</Link> },
              { key: "status", label: "Agent status", render: (row) => <StatusBadge status={row.status} /> },
              { key: "progress", label: "Progress", render: (row) => `${row.complete_steps}/${row.total_steps}` },
              { key: "awaiting_review", label: "Awaiting review" },
              { key: "open", label: "Open", render: (row) => <Link className="font-semibold text-sky-700 hover:text-sky-900" to={`/admin/agents/${row.id}/onboarding`}>Manage</Link> },
            ]}
          />
        </Card>
      </div>
    </AdminPageShell>
  );
}

function OnboardingDetail({ agentId }) {
  const { token } = useAuth();
  const agent = useAgent(agentId);
  const onboarding = useApiResource(`/agents/${agentId}/onboarding`, {
    initialData: [],
    fallbackError: "We could not load onboarding progress.",
  });
  const [selectedId, setSelectedId] = useState(null);
  const [form, setForm] = useState({
    completion_status: "In Progress",
    due_date: "",
    evidence_file_or_link: "",
    admin_notes: "",
    agent_notes: "",
  });
  const [saving, setSaving] = useState(false);
  const [approving, setApproving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const rows = onboarding.data || [];
  const selected = rows.find((item) => item.id === Number(selectedId)) || rows.find((item) => item.completion_status === "Awaiting Review") || rows[0];
  const completeCount = rows.filter((item) => item.completion_status === "Complete").length;

  useEffect(() => {
    if (!selectedId && selected?.id) {
      setSelectedId(selected.id);
    }
  }, [selected, selectedId]);

  useEffect(() => {
    if (selected) {
      setForm({
        completion_status: selected.completion_status || "In Progress",
        due_date: selected.due_date || "",
        evidence_file_or_link: selected.evidence_file_or_link || "",
        admin_notes: selected.admin_notes || "",
        agent_notes: selected.agent_notes || "",
      });
    }
  }, [selected]);

  async function saveProgress(event) {
    event.preventDefault();
    if (!selected) return;

    setSaving(true);
    setError("");
    setMessage("");

    try {
      await apiClient.put(
        `/agents/${agentId}/onboarding/${selected.id}`,
        {
          ...form,
          due_date: form.due_date || null,
        },
        token,
      );
      await onboarding.reload();
      setMessage("Onboarding step saved.");
    } catch (err) {
      setError(getFriendlyError(err, "We could not save this onboarding step."));
    } finally {
      setSaving(false);
    }
  }

  async function approveStep() {
    if (!selected) return;

    setApproving(true);
    setError("");
    setMessage("");

    try {
      await apiClient.post(`/agents/${agentId}/onboarding/${selected.id}/approve`, { admin_notes: form.admin_notes }, token);
      await onboarding.reload();
      setMessage("Checklist step approved.");
    } catch (err) {
      setError(getFriendlyError(err, "We could not approve this step."));
    } finally {
      setApproving(false);
    }
  }

  if (agent.loading || onboarding.loading) {
    return (
      <AdminPageShell title="Onboarding Management" description="Loading selected checklist.">
        <LoadingState message="Loading onboarding detail..." />
      </AdminPageShell>
    );
  }

  return (
    <AdminPageShell
      title="Onboarding Management"
      description={agent.data ? `Manage checklist progress for ${buildAgentName(agent.data)}.` : "Manage agent checklist progress."}
      actions={<AdminLinkButton to="/admin/onboarding">All onboarding</AdminLinkButton>}
    >
      <div className="space-y-6">
        <ErrorBanner message={agent.error || onboarding.error || error} />
        {message ? <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm font-medium text-emerald-700">{message}</div> : null}

        <Card title="Checklist Progress">
          <ProgressBar value={percentage(completeCount, rows.length)} label={`${completeCount} of ${rows.length} steps complete`} />
        </Card>

        <Card title="Checklist Items">
          <DataTable
            rows={rows}
            emptyMessage="No checklist steps are assigned yet."
            columns={[
              { key: "step", label: "Step", render: (row) => row.step?.title || "Step" },
              { key: "completion_status", label: "Status", render: (row) => <StatusBadge status={row.completion_status} /> },
              { key: "approval", label: "Approval", render: (row) => (row.step?.approval_required ? "Required" : "Not required") },
              { key: "due_date", label: "Due", render: (row) => formatDate(row.due_date) },
              { key: "evidence_file_or_link", label: "Evidence", render: (row) => <EvidenceLink value={row.evidence_file_or_link} /> },
              { key: "approved_date", label: "Approved", render: (row) => formatDate(row.approved_date) },
              { key: "select", label: "Select", render: (row) => <button type="button" className="font-semibold text-sky-700 hover:text-sky-900" onClick={() => setSelectedId(row.id)}>Edit</button> },
            ]}
          />
        </Card>

        {selected ? (
          <form onSubmit={saveProgress}>
            <Card title={`Edit Step: ${selected.step?.title || "Checklist step"}`}>
              <div className="grid gap-4 md:grid-cols-2">
                <FormField label="Status">
                  <SelectInput value={form.completion_status} onChange={(event) => setForm((current) => ({ ...current, completion_status: event.target.value }))}>
                    {onboardingStatuses.map((status) => <option key={status} value={status}>{status}</option>)}
                  </SelectInput>
                </FormField>
                <FormField label="Due date">
                  <TextInput type="date" value={form.due_date} onChange={(event) => setForm((current) => ({ ...current, due_date: event.target.value }))} />
                </FormField>
                <FormField label="Evidence file or link">
                  <TextInput value={form.evidence_file_or_link} onChange={(event) => setForm((current) => ({ ...current, evidence_file_or_link: event.target.value }))} />
                </FormField>
                <FormField label="Agent notes">
                  <TextArea value={form.agent_notes} onChange={(event) => setForm((current) => ({ ...current, agent_notes: event.target.value }))} />
                </FormField>
                <div className="md:col-span-2">
                  <FormField label="Admin notes">
                    <TextArea value={form.admin_notes} onChange={(event) => setForm((current) => ({ ...current, admin_notes: event.target.value }))} />
                  </FormField>
                </div>
              </div>
              <div className="mt-4 flex flex-wrap gap-3">
                <PrimaryButton type="submit" icon={Save} disabled={saving}>{saving ? "Saving..." : "Save step"}</PrimaryButton>
                <PrimaryButton type="button" icon={CheckCircle2} disabled={approving} onClick={approveStep}>{approving ? "Approving..." : "Approve step"}</PrimaryButton>
              </div>
            </Card>
          </form>
        ) : null}
      </div>
    </AdminPageShell>
  );
}
