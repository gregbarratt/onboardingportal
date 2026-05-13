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
import { API_BASE_URL, apiClient } from "../../api/client.js";
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
  file: null,
  file_name: "",
  file_url: "",
  requires_signature: false,
  signed: false,
  signed_date: "",
  expiry_date: "",
  notes: "",
};

function documentUrl(fileUrl) {
  if (!fileUrl) return "#";
  return fileUrl.startsWith("/") ? `${API_BASE_URL}${fileUrl}` : fileUrl;
}

function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = String(reader.result || "");
      resolve(result.includes(",") ? result.split(",", 2)[1] : result);
    };
    reader.onerror = () => reject(new Error("The selected file could not be read."));
    reader.readAsDataURL(file);
  });
}

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
  const [fileInputKey, setFileInputKey] = useState(0);

  async function handleSubmit(event) {
    event.preventDefault();
    setSaving(true);
    setSaveError("");
    setSaveMessage("");

    try {
      const hasUploadedFile = Boolean(form.file);
      const hasFileLink = Boolean(form.file_url.trim());

      if (!hasUploadedFile && !hasFileLink) {
        throw new Error("Please upload a file or add an existing file link.");
      }

      if (hasUploadedFile) {
        const fileContentBase64 = await fileToBase64(form.file);

        await apiClient.post(
          `/agents/${profile.id}/documents/upload`,
          {
            document_type: form.document_type,
            file_name: form.file.name,
            file_content_base64: fileContentBase64,
            content_type: form.file.type,
            requires_signature: form.requires_signature,
            signed: form.signed,
            signed_date: form.signed_date || null,
            expiry_date: form.expiry_date || null,
            notes: form.notes,
          },
          token,
        );
      } else {
        const { file, ...documentPayload } = form;
        await apiClient.post(
          `/agents/${profile.id}/documents`,
          {
            ...documentPayload,
            signed_date: form.signed_date || null,
            expiry_date: form.expiry_date || null,
          },
          token,
        );
      }

      setForm(blankDocument);
      setFileInputKey((current) => current + 1);
      await documents.reload();
      setSaveMessage(hasUploadedFile ? "Document uploaded for admin review." : "Document record added.");
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

      <Card title="Add Document" description="Contracts, ID, proof of address, policies, and certificates.">
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
          <FormField label="Upload file" help="PDF, Word, JPG or PNG. Maximum 10MB.">
            <input
              key={fileInputKey}
              type="file"
              accept=".pdf,.doc,.docx,.jpg,.jpeg,.png"
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 shadow-sm file:mr-3 file:rounded-md file:border-0 file:bg-sky-50 file:px-3 file:py-1.5 file:text-sm file:font-semibold file:text-sky-700"
              onChange={(event) => setForm((current) => ({ ...current, file: event.target.files?.[0] || null }))}
            />
          </FormField>
          <FormField label="File name">
            <TextInput
              required={!form.file}
              value={form.file_name}
              onChange={(event) => setForm((current) => ({ ...current, file_name: event.target.value }))}
              placeholder={form.file ? form.file.name : ""}
              disabled={Boolean(form.file)}
            />
          </FormField>
          <FormField label="Existing file link">
            <TextInput
              required={!form.file}
              value={form.file_url}
              onChange={(event) => setForm((current) => ({ ...current, file_url: event.target.value }))}
              placeholder="https://..."
              disabled={Boolean(form.file)}
            />
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
                <a className="font-semibold text-sky-700 hover:text-sky-900" href={documentUrl(row.file_url)} target="_blank" rel="noreferrer">
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
