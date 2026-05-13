import { Upload } from "lucide-react";
import { useState } from "react";

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
import { getFriendlyError, useAgentResource } from "../../hooks/useAgentPortalData.js";
import { formatDate } from "../../utils/formatters.js";
import AgentPageShell from "./AgentPageShell.jsx";

const documentTypes = [
  "Contractor Agreement",
  "Membership Terms",
  "ID Document",
  "Proof of Address",
  "Bank Details Confirmation",
  "Social Media Policy",
  "GDPR Policy",
  "Compliance Policy",
  "Training Certificate",
  "Other",
];

const blankDocument = {
  document_type: "ID Document",
  file_name: "",
  file_url: "",
  requires_signature: false,
  signed: false,
  signed_date: "",
  expiry_date: "",
  notes: "",
};

export default function DocumentsAgreementsPage() {
  return (
    <AgentPageShell
      title="Documents & Agreements"
      description="Store contracts, ID, proof of address, policy documents, and certificates for admin review."
    >
      {({ profile }) => <DocumentsContent profile={profile} />}
    </AgentPageShell>
  );
}

function DocumentsContent({ profile }) {
  const { token } = useAuth();
  const documents = useAgentResource(profile, (id) => `/agents/${id}/documents`, {
    initialData: [],
  });
  const [form, setForm] = useState(blankDocument);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState("");
  const [saveMessage, setSaveMessage] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();
    setSaving(true);
    setSaveError("");
    setSaveMessage("");

    try {
      await apiClient.post(
        `/agents/${profile.id}/documents`,
        {
          ...form,
          signed_date: form.signed_date || null,
          expiry_date: form.expiry_date || null,
        },
        token,
      );
      setForm(blankDocument);
      await documents.reload();
      setSaveMessage("Document record added.");
    } catch (err) {
      setSaveError(getFriendlyError(err, "We could not add this document."));
    } finally {
      setSaving(false);
    }
  }

  if (documents.loading) {
    return <LoadingState message="Loading documents..." />;
  }

  const rows = documents.data || [];

  return (
    <div className="space-y-6">
      <ErrorBanner message={documents.error || saveError} />
      {saveMessage ? (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm font-medium text-emerald-700">
          {saveMessage}
        </div>
      ) : null}

      <Card title="Add Document" description="This records a document link. Real file upload storage can be added in a later deployment step.">
        <form onSubmit={handleSubmit} className="grid gap-4 md:grid-cols-2">
          <FormField label="Document type">
            <SelectInput value={form.document_type} onChange={(event) => setForm((current) => ({ ...current, document_type: event.target.value }))}>
              {documentTypes.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </SelectInput>
          </FormField>
          <FormField label="File name">
            <TextInput required value={form.file_name} onChange={(event) => setForm((current) => ({ ...current, file_name: event.target.value }))} />
          </FormField>
          <FormField label="File link">
            <TextInput required value={form.file_url} onChange={(event) => setForm((current) => ({ ...current, file_url: event.target.value }))} placeholder="https://..." />
          </FormField>
          <FormField label="Expiry date">
            <TextInput type="date" value={form.expiry_date} onChange={(event) => setForm((current) => ({ ...current, expiry_date: event.target.value }))} />
          </FormField>
          <FormField label="Signed date">
            <TextInput type="date" value={form.signed_date} onChange={(event) => setForm((current) => ({ ...current, signed_date: event.target.value, signed: Boolean(event.target.value) }))} />
          </FormField>
          <div className="flex items-end gap-4">
            <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
              <input
                type="checkbox"
                checked={form.requires_signature}
                onChange={(event) => setForm((current) => ({ ...current, requires_signature: event.target.checked }))}
              />
              Requires signature
            </label>
            <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
              <input type="checkbox" checked={form.signed} onChange={(event) => setForm((current) => ({ ...current, signed: event.target.checked }))} />
              Signed
            </label>
          </div>
          <div className="md:col-span-2">
            <FormField label="Notes">
              <TextArea value={form.notes} onChange={(event) => setForm((current) => ({ ...current, notes: event.target.value }))} />
            </FormField>
          </div>
          <div className="md:col-span-2">
            <PrimaryButton type="submit" icon={Upload} disabled={saving}>
              {saving ? "Adding..." : "Add document"}
            </PrimaryButton>
          </div>
        </form>
      </Card>

      <Card title="My Documents">
        <DataTable
          rows={rows}
          emptyMessage="No documents have been added yet."
          columns={[
            { key: "document_type", label: "Type" },
            {
              key: "file_name",
              label: "File",
              render: (row) => (
                <a className="font-semibold text-sky-700 hover:text-sky-900" href={row.file_url} target="_blank" rel="noreferrer">
                  {row.file_name}
                </a>
              ),
            },
            { key: "status", label: "Status", render: (row) => <StatusBadge status={row.status} /> },
            { key: "uploaded_date", label: "Uploaded", render: (row) => formatDate(row.uploaded_date) },
            { key: "expiry_date", label: "Expiry", render: (row) => formatDate(row.expiry_date) },
            { key: "verified", label: "Verified", render: (row) => (row.verified ? "Yes" : "No") },
          ]}
        />
      </Card>
    </div>
  );
}
