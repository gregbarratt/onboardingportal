import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { Card, DataTable, ErrorBanner, LoadingState, SelectInput, StatusBadge } from "../../components/ui.jsx";
import { buildAgentName, useAdminAgentRecords, useAgents } from "../../hooks/useAdminData.js";
import { formatDate } from "../../utils/formatters.js";
import { attendanceStatuses } from "./adminConstants.js";
import AdminPageShell from "./AdminPageShell.jsx";

export default function AdminAttendanceLogsPage() {
  const [searchParams] = useSearchParams();
  const agents = useAgents();
  const attendance = useAdminAgentRecords(agents.data, "attendance");
  const [status, setStatus] = useState("All");
  const selectedAgentId = searchParams.get("agent") || "All";

  const rows = useMemo(() => {
    return attendance.records.filter((row) => {
      const matchesStatus = status === "All" || row.attendance_status === status;
      const matchesAgent = selectedAgentId === "All" || String(row.agent_id) === selectedAgentId;
      return matchesStatus && matchesAgent;
    });
  }, [attendance.records, selectedAgentId, status]);

  if (agents.loading || attendance.loading) {
    return (
      <AdminPageShell title="Attendance Logs" description="Loading attendance logs.">
        <LoadingState message="Loading attendance records..." />
      </AdminPageShell>
    );
  }

  return (
    <AdminPageShell title="Attendance Logs" description="Review live call attendance across all agents.">
      <div className="space-y-6">
        <ErrorBanner message={agents.error || attendance.error} />
        <Card title="Filters">
          <div className="grid gap-4 md:grid-cols-2">
            <label className="block">
              <span className="text-sm font-medium text-slate-700">Status</span>
              <SelectInput value={status} onChange={(event) => setStatus(event.target.value)}>
                <option value="All">All statuses</option>
                {attendanceStatuses.map((item) => <option key={item} value={item}>{item}</option>)}
              </SelectInput>
            </label>
            <div>
              <p className="text-sm font-medium text-slate-700">Agent filter</p>
              <p className="mt-2 text-sm text-slate-600">{selectedAgentId === "All" ? "All agents" : `Agent ID ${selectedAgentId}`}</p>
            </div>
          </div>
        </Card>

        <Card title="Attendance Records">
          <DataTable
            rows={rows}
            emptyMessage="No attendance records match this view."
            columns={[
              { key: "agent", label: "Agent", render: (row) => buildAgentName(row.agent) },
              { key: "session", label: "Session", render: (row) => row.session?.title || "Session" },
              { key: "session_type", label: "Type", render: (row) => row.session?.session_type || "Not set" },
              { key: "attendance_status", label: "Status", render: (row) => <StatusBadge status={row.attendance_status} /> },
              { key: "marked_date", label: "Marked", render: (row) => formatDate(row.marked_date) },
              { key: "duration_attended", label: "Minutes", render: (row) => row.duration_attended || "Not set" },
            ]}
          />
        </Card>
      </div>
    </AdminPageShell>
  );
}
