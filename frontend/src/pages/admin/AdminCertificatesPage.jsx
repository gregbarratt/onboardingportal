import { Ban, Clock, Plus } from "lucide-react";
import { useState } from "react";

import { Card, DataTable, ErrorBanner, FormField, LoadingState, PrimaryButton, SelectInput, StatusBadge, TextInput } from "../../components/ui.jsx";
import { apiClient } from "../../api/client.js";
import { useAuth } from "../../context/AuthContext.jsx";
import { buildAgentName, useAdminAgentRecords, useAgents } from "../../hooks/useAdminData.js";
import { getFriendlyError, useApiResource } from "../../hooks/useAgentPortalData.js";
import { formatDate } from "../../utils/formatters.js";
import AdminPageShell from "./AdminPageShell.jsx";

const blankCertificate = {
  agent_id: "",
  training_module_id: "",
  certificate_name: "",
  certificate_url: "",
  issued_date: "",
  expiry_date: "",
  renewal_required: false,
};

export default function AdminCertificatesPage() {
  const { token } = useAuth();
  const agents = useAgents();
  const certificates = useAdminAgentRecords(agents.data, "certificates");
  const modules = useApiResource("/training/modules", { initialData: [] });
  const [form, setForm] = useState(blankCertificate);
  const [busyId, setBusyId] = useState(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  function update(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function createCertificate(event) {
    event.preventDefault();
    setSaving(true);
    setMessage("");
    setError("");

    try {
      await apiClient.post(
        `/agents/${form.agent_id}/certificates`,
        {
          training_module_id: Number(form.training_module_id),
          certificate_name: form.certificate_name,
          certificate_url: form.certificate_url,
          issued_date: form.issued_date || null,
          expiry_date: form.expiry_date || null,
          renewal_required: form.renewal_required,
        },
        token,
      );
      setForm(blankCertificate);
      await certificates.reload();
      setMessage("Certificate created.");
    } catch (err) {
      setError(getFriendlyError(err, "We could not create this certificate."));
    } finally {
      setSaving(false);
    }
  }

  async function changeCertificate(certificateId, action) {
    setBusyId(certificateId);
    setMessage("");
    setError("");

    try {
      await apiClient.post(`/certificates/${certificateId}/${action}`, {}, token);
      await certificates.reload();
      setMessage(action === "expire" ? "Certificate expired." : "Certificate revoked.");
    } catch (err) {
      setError(getFriendlyError(err, "We could not update this certificate."));
    } finally {
      setBusyId(null);
    }
  }

  if (agents.loading || certificates.loading || modules.loading) {
    return (
      <AdminPageShell title="Certificates" description="Loading certificate records.">
        <LoadingState message="Loading certificates..." />
      </AdminPageShell>
    );
  }

  return (
    <AdminPageShell title="Certificates" description="Create, expire, and revoke training certificate records.">
      <div className="space-y-6">
        <ErrorBanner message={agents.error || certificates.error || modules.error || error} />
        {message ? <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm font-medium text-emerald-700">{message}</div> : null}

        <Card title="Create Certificate">
          <form onSubmit={createCertificate} className="grid gap-4 md:grid-cols-3">
            <FormField label="Agent">
              <SelectInput required value={form.agent_id} onChange={(event) => update("agent_id", event.target.value)}>
                <option value="">Choose agent</option>
                {(agents.data || []).map((agent) => <option key={agent.id} value={agent.id}>{buildAgentName(agent)}</option>)}
              </SelectInput>
            </FormField>
            <FormField label="Training module">
              <SelectInput required value={form.training_module_id} onChange={(event) => update("training_module_id", event.target.value)}>
                <option value="">Choose module</option>
                {(modules.data || []).map((module) => <option key={module.id} value={module.id}>{module.title}</option>)}
              </SelectInput>
            </FormField>
            <FormField label="Certificate name">
              <TextInput required value={form.certificate_name} onChange={(event) => update("certificate_name", event.target.value)} />
            </FormField>
            <FormField label="Certificate URL">
              <TextInput required value={form.certificate_url} onChange={(event) => update("certificate_url", event.target.value)} />
            </FormField>
            <FormField label="Issued date">
              <TextInput type="date" value={form.issued_date} onChange={(event) => update("issued_date", event.target.value)} />
            </FormField>
            <FormField label="Expiry date">
              <TextInput type="date" value={form.expiry_date} onChange={(event) => update("expiry_date", event.target.value)} />
            </FormField>
            <div className="flex items-end">
              <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
                <input type="checkbox" checked={form.renewal_required} onChange={(event) => update("renewal_required", event.target.checked)} />
                Renewal required
              </label>
            </div>
            <div className="md:col-span-3">
              <PrimaryButton type="submit" icon={Plus} disabled={saving}>{saving ? "Creating..." : "Create certificate"}</PrimaryButton>
            </div>
          </form>
        </Card>

        <Card title="Certificate Records">
          <DataTable
            rows={certificates.records}
            emptyMessage="No certificates have been created yet."
            columns={[
              { key: "agent", label: "Agent", render: (row) => buildAgentName(row.agent) },
              { key: "certificate_name", label: "Certificate" },
              { key: "issued_date", label: "Issued", render: (row) => formatDate(row.issued_date) },
              { key: "expiry_date", label: "Expiry", render: (row) => formatDate(row.expiry_date) },
              { key: "status", label: "Status", render: (row) => <StatusBadge status={row.status} /> },
              {
                key: "actions",
                label: "Actions",
                render: (row) => (
                  <div className="flex flex-wrap gap-2">
                    <button type="button" disabled={busyId === row.id} className="inline-flex items-center gap-1 font-semibold text-amber-700 hover:text-amber-900" onClick={() => changeCertificate(row.id, "expire")}>
                      <Clock className="h-4 w-4" aria-hidden="true" />
                      Expire
                    </button>
                    <button type="button" disabled={busyId === row.id} className="inline-flex items-center gap-1 font-semibold text-rose-700 hover:text-rose-900" onClick={() => changeCertificate(row.id, "revoke")}>
                      <Ban className="h-4 w-4" aria-hidden="true" />
                      Revoke
                    </button>
                  </div>
                ),
              },
            ]}
          />
        </Card>
      </div>
    </AdminPageShell>
  );
}
