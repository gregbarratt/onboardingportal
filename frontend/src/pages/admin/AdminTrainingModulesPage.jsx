import { Archive, Pencil, Send } from "lucide-react";
import { Link } from "react-router-dom";

import { Card, DataTable, ErrorBanner, LoadingState, StatusBadge } from "../../components/ui.jsx";
import { apiClient } from "../../api/client.js";
import { useAuth } from "../../context/AuthContext.jsx";
import { useApiResource } from "../../hooks/useAgentPortalData.js";
import { formatDate } from "../../utils/formatters.js";
import AdminPageShell, { AdminLinkButton } from "./AdminPageShell.jsx";

export default function AdminTrainingModulesPage() {
  const { token } = useAuth();
  const modules = useApiResource("/training/modules", {
    initialData: [],
    fallbackError: "We could not load training modules.",
  });

  async function changeStatus(moduleId, action) {
    await apiClient.post(`/training/modules/${moduleId}/${action}`, {}, token);
    await modules.reload();
  }

  if (modules.loading) {
    return (
      <AdminPageShell title="Training Module List" description="Loading training modules.">
        <LoadingState message="Loading training modules..." />
      </AdminPageShell>
    );
  }

  return (
    <AdminPageShell
      title="Training Module List"
      description="Create, edit, publish, or archive training modules used during onboarding."
      actions={<AdminLinkButton to="/admin/training/new">New module</AdminLinkButton>}
    >
      <div className="space-y-6">
        <ErrorBanner message={modules.error} />
        <Card title="Modules">
          <DataTable
            rows={modules.data || []}
            emptyMessage="No training modules have been created yet."
            columns={[
              { key: "title", label: "Module", render: (row) => <Link className="font-semibold text-sky-700 hover:text-sky-900" to={`/admin/training/${row.id}/edit`}>{row.title}</Link> },
              { key: "category", label: "Category", render: (row) => row.category?.name || "Not set" },
              { key: "mandatory", label: "Mandatory", render: (row) => (row.mandatory ? "Yes" : "No") },
              { key: "training_track", label: "Track" },
              { key: "published_status", label: "Status", render: (row) => <StatusBadge status={row.published_status} /> },
              { key: "updated_date", label: "Updated", render: (row) => formatDate(row.updated_date) },
              {
                key: "actions",
                label: "Actions",
                render: (row) => (
                  <div className="flex flex-wrap gap-2">
                    <Link className="inline-flex items-center gap-1 font-semibold text-sky-700 hover:text-sky-900" to={`/admin/training/${row.id}/edit`}>
                      <Pencil className="h-4 w-4" aria-hidden="true" />
                      Edit
                    </Link>
                    <button type="button" className="inline-flex items-center gap-1 font-semibold text-emerald-700 hover:text-emerald-900" onClick={() => changeStatus(row.id, "publish")}>
                      <Send className="h-4 w-4" aria-hidden="true" />
                      Publish
                    </button>
                    <button type="button" className="inline-flex items-center gap-1 font-semibold text-rose-700 hover:text-rose-900" onClick={() => changeStatus(row.id, "archive")}>
                      <Archive className="h-4 w-4" aria-hidden="true" />
                      Archive
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
