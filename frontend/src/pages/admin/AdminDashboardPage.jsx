import {
  AlertTriangle,
  CalendarX,
  CheckCircle2,
  Clock3,
  CreditCard,
  ShieldAlert,
  UserCheck,
  UserRoundCheck,
  UsersRound,
} from "lucide-react";
import { Link } from "react-router-dom";

import { Card, ErrorBanner, LoadingState, StatCard, StatusBadge } from "../../components/ui.jsx";
import { useApiResource } from "../../hooks/useAgentPortalData.js";
import AdminPageShell from "./AdminPageShell.jsx";

export default function AdminDashboardPage() {
  const dashboard = useApiResource("/admin/dashboard-summary", {
    fallbackError: "We could not load the admin dashboard.",
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

        <div className="grid gap-6 xl:grid-cols-[1fr_1fr]">
          <Card title="Approval Queue" description="Agents waiting for review or final trading approval.">
            <div className="space-y-3">
              {approvalQueue.map((agent) => (
                  <Link key={agent.id} to={`/admin/agents/${agent.id}`} className="flex items-center justify-between gap-3 rounded-lg border border-slate-200 p-3 hover:bg-slate-50">
                    <div>
                      <p className="font-medium text-slate-950">{agent.first_name} {agent.last_name}</p>
                      <p className="text-sm text-slate-500">{agent.email}</p>
                    </div>
                    <StatusBadge status={agent.status} />
                  </Link>
                ))}
              {!approvalQueue.length ? (
                <p className="text-sm text-slate-600">No urgent approval items are visible yet.</p>
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

function Shortcut({ to, label, detail }) {
  return (
    <Link to={to} className="rounded-lg border border-slate-200 p-4 transition hover:border-sky-300 hover:bg-sky-50">
      <p className="text-sm font-semibold text-slate-950">{label}</p>
      <p className="mt-1 text-sm text-slate-600">{detail}</p>
    </Link>
  );
}
