import { CheckCircle2, MessageSquarePlus, RotateCcw, Save, ShieldCheck, XCircle } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import {
  Card,
  DataTable,
  ErrorBanner,
  FormField,
  LoadingState,
  PrimaryButton,
  SecondaryButton,
  SelectInput,
  StatusBadge,
  TextArea,
  TextInput,
} from "../../components/ui.jsx";
import { apiClient } from "../../api/client.js";
import { useAuth } from "../../context/AuthContext.jsx";
import { buildAgentName, useAgent } from "../../hooks/useAdminData.js";
import { getFriendlyError, useApiResource } from "../../hooks/useAgentPortalData.js";
import { formatDateTime } from "../../utils/formatters.js";
import { agentStatuses } from "./adminConstants.js";
import AdminPageShell, { AdminLinkButton } from "./AdminPageShell.jsx";

export default function AdminAgentDetailPage() {
  const { agentId } = useParams();
  const { token } = useAuth();
  const agent = useAgent(agentId);
  const notes = useApiResource(agentId ? `/agents/${agentId}/admin-notes` : "", {
    enabled: Boolean(agentId),
    initialData: [],
    fallbackError: "We could not load admin notes.",
  });
  const finalApproval = useApiResource(agentId ? `/agents/${agentId}/final-approval` : "", {
    enabled: Boolean(agentId),
    fallbackError: "We could not load the final approval checks.",
  });
  const trainingProgress = useApiResource(agentId ? `/agents/${agentId}/training` : "", {
    enabled: Boolean(agentId),
    initialData: [],
    fallbackError: "We could not load this agent's training results.",
  });
  const [form, setForm] = useState({});
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);
  const [addingNote, setAddingNote] = useState(false);
  const [approving, setApproving] = useState(false);
  const [redoingTrainingId, setRedoingTrainingId] = useState(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (agent.data) {
      setForm({
        first_name: agent.data.first_name || "",
        last_name: agent.data.last_name || "",
        email: agent.data.email || "",
        personal_email: agent.data.personal_email || "",
        company_email: agent.data.company_email || "",
        portal_access_enabled: Boolean(agent.data.portal_access_enabled),
        phone: agent.data.phone || "",
        business_name: agent.data.business_name || "",
        status: agent.data.status || "Registered",
        address: agent.data.address || "",
        postcode: agent.data.postcode || "",
      });
    }
  }, [agent.data]);

  function updateField(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function saveAgent(event) {
    event.preventDefault();
    setSaving(true);
    setError("");
    setMessage("");

    try {
      await apiClient.put(`/agents/${agentId}`, form, token);
      await agent.reload();
      setMessage("Agent record saved.");
    } catch (err) {
      setError(getFriendlyError(err, "We could not save this agent."));
    } finally {
      setSaving(false);
    }
  }

  async function addNote(event) {
    event.preventDefault();
    setAddingNote(true);
    setError("");
    setMessage("");

    try {
      await apiClient.post(`/agents/${agentId}/admin-notes`, { note }, token);
      setNote("");
      await notes.reload();
      setMessage("Admin note added.");
    } catch (err) {
      setError(getFriendlyError(err, "We could not add this note."));
    } finally {
      setAddingNote(false);
    }
  }

  async function approveToTrade() {
    setApproving(true);
    setError("");
    setMessage("");

    try {
      await apiClient.post(`/agents/${agentId}/approve-to-trade`, {}, token);
      await Promise.all([agent.reload(), finalApproval.reload()]);
      setMessage("Agent approved to trade.");
    } catch (err) {
      setError(getFriendlyError(err, "We could not approve this agent yet."));
    } finally {
      setApproving(false);
    }
  }

  async function requestTrainingRedo(progressId) {
    setRedoingTrainingId(progressId);
    setError("");
    setMessage("");

    try {
      await apiClient.post(
        `/agents/${agentId}/training/${progressId}/redo`,
        { notes: "Admin requested this training module to be completed again." },
        token,
      );
      await trainingProgress.reload();
      setMessage("Training redo requested.");
    } catch (err) {
      setError(getFriendlyError(err, "We could not request this training redo."));
    } finally {
      setRedoingTrainingId(null);
    }
  }

  if (agent.loading) {
    return (
      <AdminPageShell title="Agent Detail" description="Loading the selected agent.">
        <LoadingState message="Loading agent detail..." />
      </AdminPageShell>
    );
  }

  const selectedAgent = agent.data;

  return (
    <AdminPageShell
      title={selectedAgent ? buildAgentName(selectedAgent) : "Agent Detail"}
      description="Review profile details, status, internal notes, and links to the agent's admin records."
      actions={<AdminLinkButton to="/admin/agents">Back to agents</AdminLinkButton>}
    >
      <div className="space-y-6">
        <ErrorBanner message={agent.error || notes.error || finalApproval.error || trainingProgress.error || error} />
        {message ? <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm font-medium text-emerald-700">{message}</div> : null}

        {selectedAgent ? (
          <div className="grid gap-6 xl:grid-cols-[0.8fr_1.2fr]">
            <Card title="Agent Snapshot">
              <dl className="space-y-3 text-sm">
                <Detail label="Status" value={<StatusBadge status={selectedAgent.status} />} />
                <Detail label="Agent ID" value={selectedAgent.agent_id || "Not assigned"} />
                <Detail label="Email" value={selectedAgent.email} />
                <Detail label="Personal email" value={selectedAgent.personal_email || "Not set"} />
                <Detail label="One Travel Club email" value={selectedAgent.company_email || "Not set"} />
                <Detail label="Portal access" value={selectedAgent.portal_access_enabled ? "Enabled" : "Disabled"} />
                <Detail label="Phone" value={selectedAgent.phone || "Not set"} />
                <Detail label="Business" value={selectedAgent.business_name || "Not set"} />
                <Detail label="Created" value={formatDateTime(selectedAgent.created_at)} />
              </dl>
            </Card>

            <Card title="Admin Areas">
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                <AdminAreaLink to={`/admin/agents/${agentId}/membership`} label="Membership & Payments" />
                <AdminAreaLink to={`/admin/agents/${agentId}/onboarding`} label="Onboarding" />
                <AdminAreaLink to={`/admin/attendance?agent=${agentId}`} label="Attendance" />
                <AdminAreaLink to="/admin/documents" label="Document Review" />
                <AdminAreaLink to="/admin/certificates" label="Certificates" />
                <AdminAreaLink to="/admin/audit-logs" label="Audit Logs" />
              </div>
            </Card>
          </div>
        ) : null}

        <FinalApprovalCard
          approval={finalApproval.data}
          loading={finalApproval.loading}
          approving={approving}
          onApprove={approveToTrade}
        />

        <TrainingProgressCard
          rows={trainingProgress.data || []}
          loading={trainingProgress.loading}
          redoingTrainingId={redoingTrainingId}
          onRedo={requestTrainingRedo}
        />

        <form onSubmit={saveAgent}>
          <Card title="Edit Agent Record" description="Admins can update the agent status and key contact details.">
            <div className="grid gap-4 md:grid-cols-2">
              <FormField label="First name">
                <TextInput value={form.first_name || ""} onChange={(event) => updateField("first_name", event.target.value)} />
              </FormField>
              <FormField label="Last name">
                <TextInput value={form.last_name || ""} onChange={(event) => updateField("last_name", event.target.value)} />
              </FormField>
              <FormField label="Email">
                <TextInput type="email" value={form.email || ""} onChange={(event) => updateField("email", event.target.value)} />
              </FormField>
              <FormField label="Personal email">
                <TextInput type="email" value={form.personal_email || ""} onChange={(event) => updateField("personal_email", event.target.value)} />
              </FormField>
              <FormField label="One Travel Club email">
                <TextInput type="email" value={form.company_email || ""} onChange={(event) => updateField("company_email", event.target.value)} />
              </FormField>
              <FormField label="Phone">
                <TextInput value={form.phone || ""} onChange={(event) => updateField("phone", event.target.value)} />
              </FormField>
              <FormField label="Business name">
                <TextInput value={form.business_name || ""} onChange={(event) => updateField("business_name", event.target.value)} />
              </FormField>
              <FormField label="Status">
                <SelectInput value={form.status || "Registered"} onChange={(event) => updateField("status", event.target.value)}>
                  {agentStatuses.map((status) => (
                    <option key={status} value={status}>
                      {status}
                    </option>
                  ))}
                </SelectInput>
              </FormField>
              <FormField label="Address">
                <TextArea value={form.address || ""} onChange={(event) => updateField("address", event.target.value)} />
              </FormField>
              <FormField label="Postcode">
                <TextInput value={form.postcode || ""} onChange={(event) => updateField("postcode", event.target.value)} />
              </FormField>
              <div className="md:col-span-2">
                <label className="flex items-center gap-3 rounded-lg border border-slate-200 bg-slate-50 px-3 py-3 text-sm font-medium text-slate-700">
                  <input
                    type="checkbox"
                    checked={Boolean(form.portal_access_enabled)}
                    onChange={(event) => updateField("portal_access_enabled", event.target.checked)}
                    className="h-4 w-4 rounded border-slate-300 text-sky-700 focus:ring-sky-600"
                  />
                  Agent can log in to the portal
                </label>
              </div>
            </div>
            <div className="mt-4">
              <PrimaryButton type="submit" icon={Save} disabled={saving}>
                {saving ? "Saving..." : "Save agent"}
              </PrimaryButton>
            </div>
          </Card>
        </form>

        <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
          <Card title="Add Internal Admin Note">
            <form onSubmit={addNote} className="space-y-4">
              <FormField label="Note">
                <TextArea value={note} onChange={(event) => setNote(event.target.value)} required />
              </FormField>
              <PrimaryButton type="submit" icon={MessageSquarePlus} disabled={addingNote}>
                {addingNote ? "Adding..." : "Add note"}
              </PrimaryButton>
            </form>
          </Card>

          <Card title="Admin Notes">
            <DataTable
              rows={notes.data || []}
              emptyMessage="No admin notes have been added yet."
              columns={[
                { key: "note", label: "Note" },
                { key: "created_date", label: "Created", render: (row) => formatDateTime(row.created_date) },
              ]}
            />
          </Card>
        </div>
      </div>
    </AdminPageShell>
  );
}

function TrainingProgressCard({ rows, loading, redoingTrainingId, onRedo }) {
  if (loading) {
    return (
      <Card title="Training Results" description="The portal is loading this agent's module progress and quiz results.">
        <LoadingState message="Loading training results..." />
      </Card>
    );
  }

  return (
    <Card title="Training Results" description="Admins can see pass/fail scores and ask the agent to redo a module.">
      <DataTable
        rows={rows}
        emptyMessage="No training records are available yet."
        columns={[
          {
            key: "module",
            label: "Module",
            render: (row) => row.training_module?.title || "Training module",
          },
          {
            key: "progress_status",
            label: "Status",
            render: (row) => <StatusBadge status={row.progress_status} />,
          },
          {
            key: "score",
            label: "Score",
            render: (row) => (row.score === null || row.score === undefined ? "Not scored" : `${row.score}%`),
          },
          {
            key: "passed",
            label: "Result",
            render: (row) => {
              if (row.passed === true) return <StatusBadge status="Passed" />;
              if (row.passed === false) return <StatusBadge status="Failed" />;
              return <StatusBadge status="Not attempted" />;
            },
          },
          {
            key: "notes",
            label: "Notes",
            render: (row) => row.notes || "Not set",
          },
          {
            key: "actions",
            label: "Actions",
            render: (row) => (
              <SecondaryButton
                type="button"
                icon={RotateCcw}
                disabled={redoingTrainingId === row.id}
                onClick={() => onRedo(row.id)}
              >
                {redoingTrainingId === row.id ? "Requesting..." : "Ask to redo"}
              </SecondaryButton>
            ),
          },
        ]}
      />
    </Card>
  );
}

function FinalApprovalCard({ approval, loading, approving, onApprove }) {
  if (loading) {
    return (
      <Card title="Final Approval Gate" description="The portal is checking the items needed before this agent can trade.">
        <LoadingState message="Checking final approval rules..." />
      </Card>
    );
  }

  if (!approval) {
    return null;
  }

  const statusText = approval.approved_to_trade
    ? "Approved to Trade"
    : approval.ready_for_approval
      ? "Ready for approval"
      : `${approval.missing_requirements.length} item${approval.missing_requirements.length === 1 ? "" : "s"} missing`;

  return (
    <Card
      title="Final Approval Gate"
      description="This is the final check before supplier access opens for the agent."
      actions={
        <PrimaryButton
          type="button"
          icon={ShieldCheck}
          disabled={!approval.ready_for_approval || approval.approved_to_trade || approving}
          onClick={onApprove}
        >
          {approving ? "Approving..." : "Approve to Trade"}
        </PrimaryButton>
      }
    >
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-medium text-slate-600">Approval status</p>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <StatusBadge status={statusText} />
            <StatusBadge status={approval.current_status} />
          </div>
        </div>
        {approval.ready_for_approval ? (
          <p className="rounded-lg bg-emerald-50 px-3 py-2 text-sm font-medium text-emerald-700">
            All blocking checks are complete.
          </p>
        ) : null}
      </div>

      <DataTable
        rows={approval.requirements || []}
        emptyMessage="No approval checks are available yet."
        columns={[
          {
            key: "label",
            label: "Check",
          },
          {
            key: "complete",
            label: "Result",
            render: (row) => (
              <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium ring-1 ${row.complete ? "bg-emerald-50 text-emerald-700 ring-emerald-200" : "bg-amber-50 text-amber-700 ring-amber-200"}`}>
                {row.complete ? <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" /> : <XCircle className="h-3.5 w-3.5" aria-hidden="true" />}
                {row.complete ? "Complete" : "Needed"}
              </span>
            ),
          },
          {
            key: "detail",
            label: "Detail",
            render: (row) => row.detail || "Not set",
          },
        ]}
      />
    </Card>
  );
}

function Detail({ label, value }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <dt className="text-slate-500">{label}</dt>
      <dd className="font-medium text-slate-900">{value}</dd>
    </div>
  );
}

function AdminAreaLink({ to, label }) {
  return (
    <Link to={to} className="rounded-lg border border-slate-200 p-4 text-sm font-semibold text-slate-900 transition hover:border-sky-300 hover:bg-sky-50">
      {label}
    </Link>
  );
}
