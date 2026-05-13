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
import { useAdminAgentRecords, useAgents } from "../../hooks/useAdminData.js";
import { useApiResource } from "../../hooks/useAgentPortalData.js";
import AdminPageShell from "./AdminPageShell.jsx";

export default function AdminDashboardPage() {
  const agents = useAgents();
  const compliance = useApiResource("/admin/compliance-dashboard", {
    fallbackError: "We could not load the compliance dashboard.",
  });
  const memberships = useAdminAgentRecords(agents.data, "membership");
  const training = useAdminAgentRecords(agents.data, "training");
  const attendance = useAdminAgentRecords(agents.data, "attendance");

  if (agents.loading) {
    return (
      <AdminPageShell title="Admin Dashboard" description="A quick overview of the onboarding operation.">
        <LoadingState message="Loading admin dashboard..." />
      </AdminPageShell>
    );
  }

  const agentRows = agents.data || [];
  const activeAgents = agentRows.filter((agent) => ["Approved to Trade", "Active Agent"].includes(agent.status)).length;
  const onboardingAgents = agentRows.filter((agent) => agent.status.includes("Onboarding") || agent.status.includes("Training")).length;
  const awaitingPayment = agentRows.filter((agent) => ["Payment Pending", "Payment Overdue"].includes(agent.status)).length;
  const awaitingApproval = agentRows.filter((agent) => agent.status === "Awaiting Final Approval").length;
  const failedPayments = memberships.records.filter((item) => ["Failed", "Overdue"].includes(item.payment_status)).length;
  const overdueTraining = training.records.filter((item) => ["Expired", "Failed"].includes(item.progress_status)).length;
  const missedCalls = attendance.records.filter((item) => item.attendance_status === "Missed").length;
  const complianceHold = agentRows.filter((agent) => agent.status === "Compliance Hold").length || compliance.data?.agents_on_compliance_hold || 0;
  const suspendedAgents = agentRows.filter((agent) => agent.status === "Suspended").length;

  return (
    <AdminPageShell title="Admin Dashboard" description="Monitor agent onboarding, payments, calls, training, documents, and compliance from one place.">
      <div className="space-y-6">
        <ErrorBanner message={agents.error || compliance.error || memberships.error || training.error || attendance.error} />

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
          <StatCard label="Total agents" value={agentRows.length} icon={UsersRound} />
          <StatCard label="Active agents" value={activeAgents} icon={UserRoundCheck} />
          <StatCard label="In onboarding" value={onboardingAgents} icon={Clock3} />
          <StatCard label="Awaiting payment" value={awaitingPayment} icon={CreditCard} />
          <StatCard label="Final approval" value={awaitingApproval} icon={UserCheck} />
          <StatCard label="Failed payments" value={failedPayments} icon={AlertTriangle} />
          <StatCard label="Overdue training" value={overdueTraining} icon={Clock3} />
          <StatCard label="Missed calls" value={missedCalls} icon={CalendarX} />
          <StatCard label="Compliance hold" value={complianceHold} icon={ShieldAlert} />
          <StatCard label="Suspended" value={suspendedAgents} icon={AlertTriangle} />
        </div>

        <div className="grid gap-6 xl:grid-cols-[1fr_1fr]">
          <Card title="Approval Queue" description="Agents waiting for review or final trading approval.">
            <div className="space-y-3">
              {agentRows
                .filter((agent) => ["Awaiting Final Approval", "Compliance Hold", "Payment Pending"].includes(agent.status))
                .slice(0, 6)
                .map((agent) => (
                  <Link key={agent.id} to={`/admin/agents/${agent.id}`} className="flex items-center justify-between gap-3 rounded-lg border border-slate-200 p-3 hover:bg-slate-50">
                    <div>
                      <p className="font-medium text-slate-950">{agent.first_name} {agent.last_name}</p>
                      <p className="text-sm text-slate-500">{agent.email}</p>
                    </div>
                    <StatusBadge status={agent.status} />
                  </Link>
                ))}
              {!agentRows.some((agent) => ["Awaiting Final Approval", "Compliance Hold", "Payment Pending"].includes(agent.status)) ? (
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
            </div>
          </Card>
        </div>

        {compliance.data ? (
          <Card title="Compliance Snapshot">
            <div className="grid gap-4 md:grid-cols-4">
              <StatCard label="Documents awaiting review" value={compliance.data.documents_awaiting_review} icon={CheckCircle2} />
              <StatCard label="Policy acceptances" value={compliance.data.policy_acceptance_count} icon={CheckCircle2} />
              <StatCard label="Missing document agents" value={compliance.data.missing_document_agents?.length || 0} icon={AlertTriangle} />
              <StatCard label="Expired compliance training" value={compliance.data.expired_compliance_training_agents?.length || 0} icon={Clock3} />
            </div>
          </Card>
        ) : null}
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
