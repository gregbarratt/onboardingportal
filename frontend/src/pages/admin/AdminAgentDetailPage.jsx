import { MessageSquarePlus, Save } from "lucide-react";
import { useEffect, useState } from "react";
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
  const [form, setForm] = useState({});
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);
  const [addingNote, setAddingNote] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (agent.data) {
      setForm({
        first_name: agent.data.first_name || "",
        last_name: agent.data.last_name || "",
        email: agent.data.email || "",
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
        <ErrorBanner message={agent.error || notes.error || error} />
        {message ? <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm font-medium text-emerald-700">{message}</div> : null}

        {selectedAgent ? (
          <div className="grid gap-6 xl:grid-cols-[0.8fr_1.2fr]">
            <Card title="Agent Snapshot">
              <dl className="space-y-3 text-sm">
                <Detail label="Status" value={<StatusBadge status={selectedAgent.status} />} />
                <Detail label="Agent ID" value={selectedAgent.agent_id || "Not assigned"} />
                <Detail label="Email" value={selectedAgent.email} />
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
