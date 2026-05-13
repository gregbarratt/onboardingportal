import { useMemo, useState } from "react";

import { Card, DataTable, ErrorBanner, LoadingState, TextInput } from "../../components/ui.jsx";
import { useApiResource } from "../../hooks/useAgentPortalData.js";
import { formatDateTime } from "../../utils/formatters.js";
import AdminPageShell from "./AdminPageShell.jsx";

export default function AdminAuditLogsPage() {
  const auditLogs = useApiResource("/audit-logs", {
    initialData: [],
    fallbackError: "We could not load audit logs.",
  });
  const [search, setSearch] = useState("");

  const rows = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) return auditLogs.data || [];

    return (auditLogs.data || []).filter((row) => {
      return `${row.action_type} ${row.description} ${row.previous_value || ""} ${row.new_value || ""}`.toLowerCase().includes(query);
    });
  }, [auditLogs.data, search]);

  if (auditLogs.loading) {
    return (
      <AdminPageShell title="Audit Logs" description="Loading audit logs.">
        <LoadingState message="Loading audit logs..." />
      </AdminPageShell>
    );
  }

  return (
    <AdminPageShell title="Audit Logs" description="Review the compliance history of important actions in the system.">
      <div className="space-y-6">
        <ErrorBanner message={auditLogs.error} />

        <Card title="Search Audit Logs">
          <TextInput value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search action, description, or values" />
        </Card>

        <Card title="Audit Log Records">
          <DataTable
            rows={rows}
            emptyMessage="No audit logs match this view."
            columns={[
              { key: "created_date", label: "Date", render: (row) => formatDateTime(row.created_date) },
              { key: "action_type", label: "Action" },
              { key: "agent_id", label: "Agent", render: (row) => row.agent_id || "System" },
              { key: "description", label: "Description" },
              { key: "previous_value", label: "Previous", render: (row) => row.previous_value || "Not set" },
              { key: "new_value", label: "New", render: (row) => row.new_value || "Not set" },
            ]}
          />
        </Card>
      </div>
    </AdminPageShell>
  );
}
