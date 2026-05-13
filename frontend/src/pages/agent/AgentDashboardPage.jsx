import { Award, BookOpenCheck, CalendarCheck, CheckSquare, CreditCard, FileCheck2 } from "lucide-react";
import { Link } from "react-router-dom";

import { Card, EmptyState, ErrorBanner, ProgressBar, StatCard, StatusBadge } from "../../components/ui.jsx";
import { useAgentResource } from "../../hooks/useAgentPortalData.js";
import { formatDate, fullName, percentage } from "../../utils/formatters.js";
import AgentPageShell from "./AgentPageShell.jsx";

export default function AgentDashboardPage() {
  return (
    <AgentPageShell
      title="Agent Dashboard"
      description="A simple overview of your onboarding, training, payments, documents, and next actions."
    >
      {({ profile }) => <DashboardContent profile={profile} />}
    </AgentPageShell>
  );
}

function DashboardContent({ profile }) {
  const membership = useAgentResource(profile, (id) => `/agents/${id}/membership`, {
    fallbackError: "Membership has not been set up yet.",
  });
  const onboarding = useAgentResource(profile, (id) => `/agents/${id}/onboarding`, {
    initialData: [],
  });
  const training = useAgentResource(profile, (id) => `/agents/${id}/training`, {
    initialData: [],
  });
  const attendance = useAgentResource(profile, (id) => `/agents/${id}/attendance`, {
    initialData: [],
  });
  const documents = useAgentResource(profile, (id) => `/agents/${id}/documents`, {
    initialData: [],
  });
  const certificates = useAgentResource(profile, (id) => `/agents/${id}/certificates`, {
    initialData: [],
  });

  const onboardingRows = onboarding.data || [];
  const trainingRows = training.data || [];
  const documentRows = documents.data || [];
  const attendanceRows = attendance.data || [];

  const onboardingComplete = onboardingRows.filter((item) => item.completion_status === "Complete").length;
  const mandatoryTraining = trainingRows.filter((item) => item.training_module?.mandatory);
  const mandatoryComplete = mandatoryTraining.filter((item) => item.progress_status === "Complete").length;
  const verifiedDocuments = documentRows.filter((item) => item.status === "Verified").length;
  const attendedCalls = attendanceRows.filter((item) => ["Attended", "Watched Recording"].includes(item.attendance_status)).length;

  const nextChecklistItems = onboardingRows
    .filter((item) => item.completion_status !== "Complete")
    .sort((a, b) => (a.step?.sort_order || 0) - (b.step?.sort_order || 0))
    .slice(0, 4);

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Agent status" value={profile.status || "Registered"} detail={fullName(profile)} icon={CheckSquare} />
        <StatCard
          label="Membership"
          value={membership.data?.membership_status || "Not set"}
          detail={membership.data?.next_payment_date ? `Next payment ${formatDate(membership.data.next_payment_date)}` : "Payment details will appear here"}
          icon={CreditCard}
        />
        <StatCard
          label="Onboarding"
          value={`${onboardingComplete}/${onboardingRows.length || 0}`}
          detail="Checklist steps complete"
          icon={BookOpenCheck}
        />
        <StatCard label="Certificates" value={certificates.data?.length || 0} detail="Training certificates recorded" icon={Award} />
      </div>

      {membership.error ? <ErrorBanner message={membership.error} /> : null}

      <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <Card title="Overall Progress" description="These bars give agents and admin a quick view of what is still outstanding.">
          <div className="space-y-5">
            <ProgressBar value={percentage(onboardingComplete, onboardingRows.length)} label="Onboarding checklist" />
            <ProgressBar value={percentage(mandatoryComplete, mandatoryTraining.length)} label="Mandatory training" />
            <ProgressBar value={percentage(verifiedDocuments, documentRows.length)} label="Verified documents" />
            <ProgressBar value={percentage(attendedCalls, attendanceRows.length)} label="Live call attendance" />
          </div>
        </Card>

        <Card title="Profile Snapshot">
          <dl className="space-y-3 text-sm">
            <div className="flex items-center justify-between gap-3">
              <dt className="text-slate-500">Status</dt>
              <dd>
                <StatusBadge status={profile.status} />
              </dd>
            </div>
            <div className="flex items-center justify-between gap-3">
              <dt className="text-slate-500">Agent ID</dt>
              <dd className="font-medium text-slate-900">{profile.agent_id || "Not assigned yet"}</dd>
            </div>
            <div className="flex items-center justify-between gap-3">
              <dt className="text-slate-500">Business</dt>
              <dd className="font-medium text-slate-900">{profile.business_name || "Not set"}</dd>
            </div>
            <div className="flex items-center justify-between gap-3">
              <dt className="text-slate-500">Joining date</dt>
              <dd className="font-medium text-slate-900">{formatDate(profile.joining_date)}</dd>
            </div>
          </dl>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card
          title="Next Onboarding Steps"
          actions={
            <Link className="text-sm font-semibold text-sky-700 hover:text-sky-900" to="/onboarding">
              View checklist
            </Link>
          }
        >
          {nextChecklistItems.length ? (
            <div className="space-y-3">
              {nextChecklistItems.map((item) => (
                <div key={item.id} className="rounded-lg border border-slate-200 p-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-medium text-slate-900">{item.step?.title}</p>
                      <p className="mt-1 text-sm text-slate-600">{item.step?.description || "No description added yet."}</p>
                    </div>
                    <StatusBadge status={item.completion_status} />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState title="No open checklist items" message="All visible onboarding steps are complete." />
          )}
        </Card>

        <Card title="Important Records">
          <div className="grid gap-3 sm:grid-cols-2">
            <QuickLink to="/membership" icon={CreditCard} label="Payments" detail={membership.data?.payment_status || "Not set"} />
            <QuickLink to="/documents" icon={FileCheck2} label="Documents" detail={`${verifiedDocuments} verified`} />
            <QuickLink to="/live-calls" icon={CalendarCheck} label="Live calls" detail={`${attendedCalls} attended`} />
            <QuickLink to="/certificates" icon={Award} label="Certificates" detail={`${certificates.data?.length || 0} recorded`} />
          </div>
        </Card>
      </div>
    </div>
  );
}

function QuickLink({ to, icon: Icon, label, detail }) {
  return (
    <Link to={to} className="rounded-lg border border-slate-200 p-4 transition hover:border-sky-300 hover:bg-sky-50">
      <Icon className="h-5 w-5 text-sky-700" aria-hidden="true" />
      <p className="mt-3 text-sm font-semibold text-slate-900">{label}</p>
      <p className="mt-1 text-sm text-slate-600">{detail}</p>
    </Link>
  );
}
