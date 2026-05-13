import { Search } from "lucide-react";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { Card, DataTable, ErrorBanner, LoadingState, SelectInput, StatusBadge, TextInput } from "../../components/ui.jsx";
import { buildAgentName, useAgents } from "../../hooks/useAdminData.js";
import { formatDate } from "../../utils/formatters.js";
import { agentStatuses } from "./adminConstants.js";
import AdminPageShell from "./AdminPageShell.jsx";

export default function AdminAgentListPage() {
  const agents = useAgents();
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("All");

  const filteredAgents = useMemo(() => {
    const query = search.trim().toLowerCase();

    return (agents.data || []).filter((agent) => {
      const matchesStatus = status === "All" || agent.status === status;
      const searchable = `${buildAgentName(agent)} ${agent.email} ${agent.business_name || ""} ${agent.agent_id || ""}`.toLowerCase();
      return matchesStatus && (!query || searchable.includes(query));
    });
  }, [agents.data, search, status]);

  if (agents.loading) {
    return (
      <AdminPageShell title="Agent List" description="Find and manage agent records.">
        <LoadingState message="Loading agents..." />
      </AdminPageShell>
    );
  }

  return (
    <AdminPageShell title="Agent List" description="Search agents, check their status, and open their full admin record.">
      <div className="space-y-6">
        <ErrorBanner message={agents.error} />

        <Card title="Filters">
          <div className="grid gap-4 md:grid-cols-[1fr_260px]">
            <label className="block">
              <span className="text-sm font-medium text-slate-700">Search</span>
              <div className="relative mt-1">
                <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" aria-hidden="true" />
                <TextInput className="pl-9" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Name, email, business, or agent ID" />
              </div>
            </label>
            <label className="block">
              <span className="text-sm font-medium text-slate-700">Status</span>
              <SelectInput value={status} onChange={(event) => setStatus(event.target.value)}>
                <option value="All">All statuses</option>
                {agentStatuses.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </SelectInput>
            </label>
          </div>
        </Card>

        <Card title="Agents" description={`${filteredAgents.length} agent records shown.`}>
          <DataTable
            rows={filteredAgents}
            emptyMessage="No agents match these filters."
            columns={[
              {
                key: "name",
                label: "Agent",
                render: (row) => (
                  <div>
                    <Link className="font-semibold text-sky-700 hover:text-sky-900" to={`/admin/agents/${row.id}`}>
                      {buildAgentName(row)}
                    </Link>
                    <p className="text-xs text-slate-500">{row.email}</p>
                  </div>
                ),
              },
              { key: "agent_id", label: "Agent ID" },
              { key: "business_name", label: "Business" },
              { key: "status", label: "Status", render: (row) => <StatusBadge status={row.status} /> },
              { key: "joining_date", label: "Joining date", render: (row) => formatDate(row.joining_date) },
              {
                key: "actions",
                label: "Actions",
                render: (row) => (
                  <div className="flex flex-wrap gap-2">
                    <Link className="font-semibold text-sky-700 hover:text-sky-900" to={`/admin/agents/${row.id}`}>
                      Details
                    </Link>
                    <Link className="font-semibold text-sky-700 hover:text-sky-900" to={`/admin/agents/${row.id}/membership`}>
                      Payments
                    </Link>
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
