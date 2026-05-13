import { CheckCircle2, XCircle } from "lucide-react";
import { useState } from "react";

import { Card, DataTable, ErrorBanner, LoadingState, PrimaryButton, StatusBadge } from "../../components/ui.jsx";
import { API_BASE_URL, apiClient } from "../../api/client.js";
import { useAuth } from "../../context/AuthContext.jsx";
import { buildAgentName, useAdminAgentRecords, useAgents } from "../../hooks/useAdminData.js";
import { getFriendlyError } from "../../hooks/useAgentPortalData.js";
import { formatDate } from "../../utils/formatters.js";
import AdminPageShell from "./AdminPageShell.jsx";

function documentUrl(fileUrl) {
  if (!fileUrl) return "#";
  return fileUrl.startsWith("/") ? `${API_BASE_URL}${fileUrl}` : fileUrl;
}

export default function AdminDocumentReviewPage() {
  const { token } = useAuth();
  const agents = useAgents();
  const documents = useAdminAgentRecords(agents.data, "documents");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState(null);

  async function reviewDocument(documentId, action) {
    setBusyId(documentId);
    setError("");
    setMessage("");

    try {
      await apiClient.post(`/documents/${documentId}/${action}`, {}, token);
      await documents.reload();
      setMessage(action === "verify" ? "Document verified." : "Document rejected.");
    } catch (err) {
      setError(getFriendlyError(err, "We could not update this document."));
    } finally {
      setBusyId(null);
    }
  }

  if (agents.loading || documents.loading) {
    return (
      <AdminPageShell title="Document Review" description="Loading document records.">
        <LoadingState message="Loading documents..." />
      </AdminPageShell>
    );
  }

  const awaitingReview = documents.records.filter((item) => ["Uploaded", "Awaiting Review", "Requested"].includes(item.status));

  return (
    <AdminPageShell title="Document Review" description="Verify or reject uploaded documents, agreements, ID, proof of address, and certificates.">
      <div className="space-y-6">
        <ErrorBanner message={agents.error || documents.error || error} />
        {message ? <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm font-medium text-emerald-700">{message}</div> : null}

        <Card title="Documents Awaiting Review">
          <DataTable
            rows={awaitingReview}
            emptyMessage="No documents are awaiting review."
            columns={[
              { key: "agent", label: "Agent", render: (row) => buildAgentName(row.agent) },
              { key: "document_type", label: "Type" },
              { key: "file_name", label: "File", render: (row) => <a className="font-semibold text-sky-700 hover:text-sky-900" href={documentUrl(row.file_url)} target="_blank" rel="noreferrer">{row.file_name}</a> },
              { key: "status", label: "Status", render: (row) => <StatusBadge status={row.status} /> },
              { key: "uploaded_date", label: "Uploaded", render: (row) => formatDate(row.uploaded_date) },
              {
                key: "actions",
                label: "Actions",
                render: (row) => (
                  <div className="flex flex-wrap gap-2">
                    <PrimaryButton type="button" icon={CheckCircle2} disabled={busyId === row.id} onClick={() => reviewDocument(row.id, "verify")}>
                      Verify
                    </PrimaryButton>
                    <button type="button" disabled={busyId === row.id} className="inline-flex items-center gap-2 rounded-lg border border-rose-200 bg-white px-4 py-2 text-sm font-semibold text-rose-700 hover:bg-rose-50 disabled:text-slate-400" onClick={() => reviewDocument(row.id, "reject")}>
                      <XCircle className="h-4 w-4" aria-hidden="true" />
                      Reject
                    </button>
                  </div>
                ),
              },
            ]}
          />
        </Card>

        <Card title="All Documents">
          <DataTable
            rows={documents.records}
            emptyMessage="No documents have been uploaded yet."
            columns={[
              { key: "agent", label: "Agent", render: (row) => buildAgentName(row.agent) },
              { key: "document_type", label: "Type" },
              { key: "file_name", label: "File", render: (row) => <a className="font-semibold text-sky-700 hover:text-sky-900" href={documentUrl(row.file_url)} target="_blank" rel="noreferrer">{row.file_name}</a> },
              { key: "status", label: "Status", render: (row) => <StatusBadge status={row.status} /> },
              { key: "expiry_date", label: "Expiry", render: (row) => formatDate(row.expiry_date) },
            ]}
          />
        </Card>
      </div>
    </AdminPageShell>
  );
}
