import { Send } from "lucide-react";
import { useEffect, useState } from "react";

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
import { getFriendlyError, useAgentResource } from "../../hooks/useAgentPortalData.js";
import { formatDate, percentage } from "../../utils/formatters.js";
import AgentPageShell from "./AgentPageShell.jsx";

const statusOptions = ["Not Started", "In Progress", "Awaiting Review", "Complete"];
const approvalRequiredStatusOptions = ["Not Started", "In Progress", "Awaiting Review"];

function EvidenceLink({ value }) {
  if (!value) return "Not set";

  return (
    <a className="font-semibold text-sky-700 hover:text-sky-900" href={value} target="_blank" rel="noreferrer">
      Open evidence
    </a>
  );
}

export default function OnboardingChecklistPage() {
  return (
    <AgentPageShell
      title="Onboarding Checklist"
      description="This checklist shows the steps that must be completed before an agent can be approved to trade."
    >
      {({ profile }) => <OnboardingContent profile={profile} />}
    </AgentPageShell>
  );
}

function OnboardingContent({ profile }) {
  const { token } = useAuth();
  const progress = useAgentResource(profile, (id) => `/agents/${id}/onboarding`, {
    initialData: [],
  });
  const [selectedId, setSelectedId] = useState(null);
  const [form, setForm] = useState({
    completion_status: "In Progress",
    evidence_file_or_link: "",
    agent_notes: "",
  });
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState("");
  const [saveMessage, setSaveMessage] = useState("");

  const rows = progress.data || [];
  const selectedProgress = rows.find((item) => item.id === Number(selectedId)) || rows.find((item) => item.completion_status !== "Complete") || rows[0];
  const completedCount = rows.filter((item) => item.completion_status === "Complete").length;
  const availableStatusOptions = selectedProgress?.step?.approval_required ? approvalRequiredStatusOptions : statusOptions;

  useEffect(() => {
    if (!selectedId && selectedProgress?.id) {
      setSelectedId(selectedProgress.id);
    }
  }, [selectedId, selectedProgress]);

  useEffect(() => {
    if (selectedProgress) {
      setForm({
        completion_status: selectedProgress.completion_status || "In Progress",
        evidence_file_or_link: selectedProgress.evidence_file_or_link || "",
        agent_notes: selectedProgress.agent_notes || "",
      });
    }
  }, [selectedProgress]);

  async function handleSubmit(event) {
    event.preventDefault();
    if (!selectedProgress) return;

    setSaving(true);
    setSaveError("");
    setSaveMessage("");

    try {
      await apiClient.put(`/agents/${profile.id}/onboarding/${selectedProgress.id}`, form, token);
      await progress.reload();
      setSaveMessage("Checklist step updated.");
    } catch (err) {
      setSaveError(getFriendlyError(err, "We could not update this checklist step."));
    } finally {
      setSaving(false);
    }
  }

  if (progress.loading) {
    return <LoadingState message="Loading onboarding checklist..." />;
  }

  return (
    <div className="space-y-6">
      <ErrorBanner message={progress.error || saveError} />

      {saveMessage ? (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm font-medium text-emerald-700">
          {saveMessage}
        </div>
      ) : null}

      <Card title="Checklist Progress" description="Submit steps that need approval for review. Admin will mark those steps complete after checking them.">
        <ProgressBar value={percentage(completedCount, rows.length)} label={`${completedCount} of ${rows.length} steps complete`} />
      </Card>

      <Card title="Checklist Items">
        <DataTable
          rows={rows}
          emptyMessage="No onboarding checklist steps have been assigned yet."
          columns={[
            { key: "title", label: "Step", render: (row) => row.step?.title || "Untitled step" },
            { key: "required", label: "Required", render: (row) => (row.step?.required ? "Yes" : "No") },
            { key: "completion_status", label: "Status", render: (row) => <StatusBadge status={row.completion_status} /> },
            { key: "due_date", label: "Due", render: (row) => formatDate(row.due_date) },
            { key: "evidence_file_or_link", label: "Evidence", render: (row) => <EvidenceLink value={row.evidence_file_or_link} /> },
            { key: "approved_date", label: "Approved", render: (row) => formatDate(row.approved_date) },
            {
              key: "action",
              label: "Update",
              render: (row) => (
                <button type="button" className="font-semibold text-sky-700 hover:text-sky-900" onClick={() => setSelectedId(row.id)}>
                  Select
                </button>
              ),
            },
          ]}
        />
      </Card>

      {selectedProgress ? (
        <Card title={`Update: ${selectedProgress.step?.title || "Checklist step"}`}>
          <form onSubmit={handleSubmit} className="grid gap-4 md:grid-cols-2">
            <FormField label="Status">
              <SelectInput value={form.completion_status} onChange={(event) => setForm((current) => ({ ...current, completion_status: event.target.value }))}>
                {availableStatusOptions.map((status) => (
                  <option key={status} value={status}>
                    {status}
                  </option>
                ))}
              </SelectInput>
            </FormField>
            <FormField label="Evidence file or link" help="Upload contracts and documents in Documents & Agreements, then paste the file link here if this step needs evidence.">
              <TextInput
                value={form.evidence_file_or_link}
                onChange={(event) => setForm((current) => ({ ...current, evidence_file_or_link: event.target.value }))}
                placeholder="https://..."
              />
            </FormField>
            <div className="md:col-span-2">
              <FormField label="Agent notes">
                <TextArea value={form.agent_notes} onChange={(event) => setForm((current) => ({ ...current, agent_notes: event.target.value }))} />
              </FormField>
            </div>
            <div className="md:col-span-2">
              <PrimaryButton type="submit" icon={Send} disabled={saving}>
                {saving ? "Saving..." : "Save checklist update"}
              </PrimaryButton>
            </div>
          </form>
        </Card>
      ) : null}
    </div>
  );
}
