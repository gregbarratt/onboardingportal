import {
  Activity,
  AlertTriangle,
  CalendarX,
  CheckCircle2,
  Clock3,
  Cpu,
  CreditCard,
  Database,
  HardDrive,
  ShieldAlert,
  Server,
  UserCheck,
  UserRoundCheck,
  UsersRound,
} from "lucide-react";
import { Link } from "react-router-dom";

import { Card, DataTable, ErrorBanner, LoadingState, StatCard, StatusBadge } from "../../components/ui.jsx";
import { useApiResource } from "../../hooks/useAgentPortalData.js";
import AdminPageShell from "./AdminPageShell.jsx";

export default function AdminDashboardPage() {
  const dashboard = useApiResource("/admin/dashboard-summary", {
    fallbackError: "We could not load the admin dashboard.",
  });
  const renderUsage = useApiResource("/admin/render-usage", {
    initialData: null,
    fallbackError: "We could not load Render performance data.",
  });

  if (dashboard.loading) {
    return (
      <AdminPageShell title="Admin Dashboard" description="A quick overview of the onboarding operation.">
        <LoadingState message="Loading admin dashboard..." />
      </AdminPageShell>
    );
  }

  const stats = dashboard.data || {};
  const approvalQueue = stats.approval_queue || [];
  const approvalQueueTotal = stats.approval_queue_total || approvalQueue.length;

  return (
    <AdminPageShell title="Admin Dashboard" description="Monitor agent onboarding, payments, calls, training, documents, and compliance from one place.">
      <div className="space-y-6">
        <ErrorBanner message={dashboard.error} />

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
          <StatCard label="Total agents" value={stats.total_agents || 0} icon={UsersRound} />
          <StatCard label="Active agents" value={stats.active_agents || 0} icon={UserRoundCheck} />
          <StatCard label="In onboarding" value={stats.in_onboarding || 0} icon={Clock3} />
          <StatCard label="Awaiting payment" value={stats.awaiting_payment || 0} icon={CreditCard} />
          <StatCard label="Final approval" value={stats.final_approval || 0} icon={UserCheck} />
          <StatCard label="Failed payments" value={stats.failed_payments || 0} icon={AlertTriangle} />
          <StatCard label="Overdue training" value={stats.overdue_training || 0} icon={Clock3} />
          <StatCard label="Missed calls" value={stats.missed_calls || 0} icon={CalendarX} />
          <StatCard label="Compliance hold" value={stats.compliance_hold || 0} icon={ShieldAlert} />
          <StatCard label="Suspended" value={stats.suspended_agents || 0} icon={AlertTriangle} />
        </div>

        <RenderUsagePanel usage={renderUsage.data} loading={renderUsage.loading} error={renderUsage.error} />

        <div className="grid gap-6 xl:grid-cols-[1fr_1fr]">
          <Card title="Admin Approval Queue" description="Documents, checklist items, and final approval tasks waiting for an admin decision.">
            <div className="space-y-3">
              {approvalQueueTotal ? (
                <p className="text-sm font-medium text-slate-600">
                  {approvalQueueTotal} approval item{approvalQueueTotal === 1 ? "" : "s"} waiting.
                </p>
              ) : null}
              {approvalQueue.map((item) => (
                  <Link key={item.id} to={item.link_url || "/admin"} className="flex items-center justify-between gap-3 rounded-lg border border-slate-200 p-3 hover:bg-slate-50">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="font-medium text-slate-950">{item.title}</p>
                        <span className="rounded-full bg-amber-50 px-2 py-0.5 text-xs font-semibold text-amber-700 ring-1 ring-amber-200">
                          {item.item_type}
                        </span>
                      </div>
                      <p className="mt-1 text-sm text-slate-600">{item.agent_name} · {item.agent_email}</p>
                      <p className="mt-1 text-xs text-slate-500">{item.detail}</p>
                    </div>
                    <StatusBadge status={item.status} />
                  </Link>
                ))}
              {!approvalQueue.length ? (
                <p className="text-sm text-slate-600">No approval items are waiting right now.</p>
              ) : null}
            </div>
          </Card>

          <Card title="Admin Shortcuts" description="Jump to common management areas.">
            <div className="grid gap-3 sm:grid-cols-2">
              <Shortcut to="/admin/agents" label="Agent list" detail="Search and open agent records" />
              <Shortcut to="/admin/membership" label="Payments" detail="Membership and payment status" />
              <Shortcut to="/admin/onboarding" label="Onboarding" detail="Checklist progress and approvals" />
              <Shortcut to="/admin/documents" label="Document review" detail="Verify or reject documents" />
              <Shortcut to="/admin/training" label="Training modules" detail="Publish and edit training" />
              <Shortcut to="/admin/supplier-access" label="Supplier access" detail="Add supplier instructions and required training" />
              <Shortcut to="/admin/compliance" label="Compliance dashboard" detail="Policy and document issues" />
              <Shortcut to="/admin/reports" label="Reports" detail="Review admin report tables" />
            </div>
          </Card>
        </div>

        <Card title="Compliance Snapshot">
          <div className="grid gap-4 md:grid-cols-4">
            <StatCard label="Documents awaiting review" value={stats.documents_awaiting_review || 0} icon={CheckCircle2} />
            <StatCard label="Policy acceptances" value={stats.policy_acceptance_count || 0} icon={CheckCircle2} />
            <StatCard label="Missing document agents" value={stats.missing_document_agents_count || 0} icon={AlertTriangle} />
            <StatCard label="Expired compliance training" value={stats.expired_compliance_training_count || 0} icon={Clock3} />
          </div>
        </Card>
      </div>
    </AdminPageShell>
  );
}

function RenderUsagePanel({ usage, loading, error }) {
  const summary = usage?.summary || {};
  const services = usage?.services || [];
  const metricErrorEntries = Object.entries(usage?.metric_errors || {}).slice(0, 4);

  return (
    <Card
      title="Render Performance Overview"
      description="Shows the live hosting services, plan names, and recent usage when a Render API key is connected."
    >
      <div className="space-y-4">
        <ErrorBanner message={error} />

        {loading ? (
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
            Loading Render usage...
          </div>
        ) : null}

        {!loading && usage?.configured === false ? (
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
            Render is not connected to this dashboard yet. Add RENDER_API_KEY to the backend service in Render, then redeploy. The portal will keep working without it.
          </div>
        ) : null}

        {!loading && usage?.configured && usage?.status === "error" ? (
          <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
            {usage.message || "Render usage could not be loaded."}
          </div>
        ) : null}

        {!loading && usage?.configured && usage?.status !== "error" ? (
          <>
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
              <StatCard label="Monitored services" value={summary.monitored_services || 0} icon={Server} />
              <StatCard label="Active services" value={summary.active_services || 0} icon={Activity} />
              <StatCard label="Highest CPU" value={formatPercent(summary.highest_cpu_percent)} detail={`Last ${usage.window_minutes || 60} minutes`} icon={Cpu} />
              <StatCard label="Highest memory" value={formatPercent(summary.highest_memory_percent)} detail="Compared with Render limit" icon={Database} />
              <StatCard label="Highest disk" value={formatPercent(summary.highest_disk_percent)} detail="Persistent disk usage" icon={HardDrive} />
            </div>

            <DataTable
              rows={services}
              emptyMessage="No Render services were returned for this account yet."
              columns={[
                { key: "name", label: "Service" },
                { key: "type", label: "Type" },
                { key: "plan", label: "Plan" },
                { key: "status", label: "Status", render: (row) => <StatusBadge status={row.status} /> },
                { key: "cpu", label: "CPU", render: (row) => formatPercent(row.metrics?.cpu_percent) },
                { key: "memory", label: "Memory", render: (row) => formatPercent(row.metrics?.memory_percent) },
                { key: "disk", label: "Disk", render: (row) => formatPercent(row.metrics?.disk_usage_percent) },
              ]}
            />

            {metricErrorEntries.length ? (
              <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
                <p className="font-semibold">Some Render usage figures were not available.</p>
                <ul className="mt-2 list-disc space-y-1 pl-5">
                  {metricErrorEntries.map(([name, message]) => (
                    <li key={name}>
                      {name}: {message}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </>
        ) : null}
      </div>
    </Card>
  );
}

function formatPercent(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "Not shown";
  }
  return `${Number(value).toFixed(1)}%`;
}

function Shortcut({ to, label, detail }) {
  return (
    <Link to={to} className="rounded-lg border border-slate-200 p-4 transition hover:border-sky-300 hover:bg-sky-50">
      <p className="text-sm font-semibold text-slate-950">{label}</p>
      <p className="mt-1 text-sm text-slate-600">{detail}</p>
    </Link>
  );
}
