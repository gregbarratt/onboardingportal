import {
  Award,
  CalendarCheck,
  CreditCard,
  FileCheck2,
  MoreVertical,
} from "lucide-react";
import { Link } from "react-router-dom";

import { EmptyState, ErrorBanner, StatusBadge } from "../../components/ui.jsx";
import { useAgentResource } from "../../hooks/useAgentPortalData.js";
import { formatDate, fullName, percentage } from "../../utils/formatters.js";
import AgentPageShell from "./AgentPageShell.jsx";

export default function AgentDashboardPage() {
  return (
    <AgentPageShell
      title="Agent Dashboard"
      description="A clear view of your training, attendance, compliance, payments, and next priorities."
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
  const certificateRows = certificates.data || [];

  const onboardingComplete = onboardingRows.filter((item) => item.completion_status === "Complete").length;
  const mandatoryTraining = trainingRows.filter((item) => item.training_module?.mandatory);
  const mandatoryComplete = mandatoryTraining.filter((item) => item.progress_status === "Complete").length;
  const verifiedDocuments = documentRows.filter((item) => item.status === "Verified").length;
  const attendedCalls = attendanceRows.filter((item) => ["Attended", "Watched Recording"].includes(item.attendance_status)).length;
  const passedTraining = trainingRows.filter((item) => item.progress_status === "Complete").length;

  const trainingProgress = percentage(mandatoryComplete, mandatoryTraining.length);
  const onboardingProgress = percentage(onboardingComplete, onboardingRows.length);
  const attendanceProgress = percentage(attendedCalls, attendanceRows.length);
  const documentProgress = percentage(verifiedDocuments, documentRows.length);
  const certificateProgress = certificateRows.length ? 100 : 0;
  const businessName = profile.business_name || "Not set";

  const nextChecklistItems = onboardingRows
    .filter((item) => item.completion_status !== "Complete")
    .sort((a, b) => (a.step?.sort_order || 0) - (b.step?.sort_order || 0))
    .slice(0, 4);

  const kpis = [
    {
      label: "Training score",
      status: `${trainingProgress}%`,
      business: businessName,
      attendance: attendanceProgress,
      score: trainingProgress,
      highlighted: true,
    },
    {
      label: "Mandatory training",
      status: mandatoryTraining.length && mandatoryComplete === mandatoryTraining.length ? "Completed" : "In progress",
      business: businessName,
      attendance: attendanceProgress,
      score: percentage(passedTraining, trainingRows.length),
    },
    {
      label: "Compliance status",
      status: documentProgress === 100 && trainingProgress === 100 ? "Completed" : "In progress",
      business: businessName,
      attendance: attendanceProgress,
      score: Math.round((documentProgress + trainingProgress) / 2),
    },
    {
      label: "Certificates status",
      status: certificateRows.length ? "Recorded" : "Not started",
      business: businessName,
      attendance: attendanceProgress,
      score: certificateProgress,
    },
  ];

  return (
    <div className="space-y-5">
      {membership.error ? <ErrorBanner message={membership.error} /> : null}

      <div className="grid gap-4 xl:grid-cols-[1.05fr_1.35fr_1fr]">
        <DashboardPanel className="xl:row-span-2" title="Training progress">
          <div className="flex h-full min-h-56 flex-col items-center justify-center gap-5">
            <RingProgress value={trainingProgress} />
            <div className="flex flex-wrap items-center justify-center gap-4 text-xs text-slate-600">
              <LegendDot color="bg-[#E83F6F]" label="Training" />
              <LegendDot color="bg-slate-400" label="Attendance" />
            </div>
          </div>
        </DashboardPanel>

        <DashboardPanel title="Training score">
          <div className="mb-2 flex items-center justify-between text-xs text-slate-500">
            <span>10%</span>
            <span>{trainingProgress}%</span>
          </div>
          <MiniLineChart value={trainingProgress} />
          <div className="mt-2 grid grid-cols-7 text-center text-[11px] text-slate-500">
            {["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((day) => (
              <span key={day}>{day}</span>
            ))}
          </div>
        </DashboardPanel>

        <DashboardPanel title="Compliance status">
          <div className="grid grid-cols-[1fr_auto] gap-4">
            <div className="space-y-2 text-sm text-slate-700">
              <p>Compliance</p>
              <p>Documents</p>
              <p>Certificates</p>
            </div>
            <VerticalComplianceBars value={Math.round((documentProgress + certificateProgress + trainingProgress) / 3)} />
          </div>
        </DashboardPanel>

        <DashboardPanel title="Attendance">
          <div className="grid grid-cols-2 gap-6 py-4 text-center">
            <div>
              <p className="text-sm text-slate-600">Attendance</p>
              <p className="mt-2 text-3xl font-semibold text-slate-950">{attendedCalls}</p>
            </div>
            <div>
              <p className="text-sm text-slate-600">Verified</p>
              <p className="mt-2 text-3xl font-semibold text-slate-950">{attendanceProgress}%</p>
            </div>
          </div>
        </DashboardPanel>

        <DashboardPanel title="Compliance status">
          <div className="space-y-3">
            <MiniBar label="Onboarding" value={onboardingProgress} />
            <MiniBar label="Training" value={trainingProgress} />
            <MiniBar label="Documents" value={documentProgress} />
          </div>
        </DashboardPanel>
      </div>

      <DashboardPanel title="Key Performance Indicators" compact>
        <div className="overflow-x-auto rounded-lg border border-[#005A83]">
          <div className="min-w-[760px] overflow-hidden">
            <div className="grid grid-cols-[1.2fr_0.8fr_1.4fr_0.7fr_0.6fr] bg-[#005A83] px-4 py-2 text-sm font-semibold text-white">
              <span>KPIs</span>
              <span>Status</span>
              <span>Business</span>
              <span>Attendance</span>
              <span>Score</span>
            </div>
            <div className="divide-y divide-white/15 bg-[#005A83]">
              {kpis.map((item) => (
                <div
                  key={item.label}
                  className={[
                    "grid grid-cols-[1.2fr_0.8fr_1.4fr_0.7fr_0.6fr] px-4 py-3 text-sm text-white",
                    item.highlighted ? "bg-[#E83F6F]" : "bg-[#00496b]",
                  ].join(" ")}
                >
                  <span>{item.label}</span>
                  <span>
                    {item.status.includes("%") ? (
                      <Sparkline />
                    ) : (
                      <span className="inline-flex rounded-full bg-white/20 px-2 py-1 text-xs font-semibold text-white ring-1 ring-white/20">
                        {item.status}
                      </span>
                    )}
                  </span>
                  <span>{item.business}</span>
                  <span>{item.attendance}%</span>
                  <span>{item.score}%</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </DashboardPanel>

      <div className="grid gap-5 lg:grid-cols-[1fr_0.9fr]">
        <DashboardPanel
          title="Next onboarding steps"
          actions={
            <Link className="text-sm font-semibold text-[#005A83] hover:text-[#00364f]" to="/onboarding">
              View checklist
            </Link>
          }
        >
          {nextChecklistItems.length ? (
            <div className="space-y-3">
              {nextChecklistItems.map((item) => (
                <div key={item.id} className="rounded-lg border border-slate-200 bg-white p-3">
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
        </DashboardPanel>

        <DashboardPanel title="Important records">
          <div className="grid gap-3 sm:grid-cols-2">
            <QuickLink to="/membership" icon={CreditCard} label="Payments" detail={membership.data?.payment_status || "Not set"} />
            <QuickLink to="/documents" icon={FileCheck2} label="Documents" detail={`${verifiedDocuments} verified`} />
            <QuickLink to="/live-calls" icon={CalendarCheck} label="Live calls" detail={`${attendedCalls} attended`} />
            <QuickLink to="/certificates" icon={Award} label="Certificates" detail={`${certificateRows.length} recorded`} />
          </div>
          <dl className="mt-4 space-y-2 rounded-lg bg-slate-50 p-3 text-sm">
            <InfoRow label="Agent" value={fullName(profile)} />
            <InfoRow label="Status" value={profile.status || "Registered"} />
            <InfoRow label="Agent ID" value={profile.agent_id || "Not assigned yet"} />
            <InfoRow label="Joining date" value={formatDate(profile.joining_date)} />
          </dl>
        </DashboardPanel>
      </div>
    </div>
  );
}

function DashboardPanel({ title, actions, children, className = "", compact = false }) {
  return (
    <section className={`rounded-lg border border-slate-300 bg-white shadow-sm ${compact ? "p-0" : "p-4"} ${className}`}>
      {(title || actions) && (
        <div className={compact ? "flex items-center justify-between px-4 py-3" : "mb-3 flex items-center justify-between gap-3"}>
          <h2 className="text-base font-semibold text-slate-950">{title}</h2>
          {actions || <MoreVertical className="h-5 w-5 text-slate-400" aria-hidden="true" />}
        </div>
      )}
      <div className={compact ? "px-0 pb-0" : ""}>{children}</div>
    </section>
  );
}

function RingProgress({ value }) {
  const radius = 56;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (value / 100) * circumference;

  return (
    <div className="relative h-44 w-44">
      <svg className="h-full w-full -rotate-90" viewBox="0 0 140 140" aria-hidden="true">
        <circle cx="70" cy="70" r={radius} fill="none" stroke="#e5e7eb" strokeWidth="18" />
        <circle
          cx="70"
          cy="70"
          r={radius}
          fill="none"
          stroke="#E83F6F"
          strokeLinecap="round"
          strokeWidth="18"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center rounded-full">
        <span className="text-4xl font-semibold text-slate-950">{value}%</span>
      </div>
    </div>
  );
}

function LegendDot({ color, label }) {
  return (
    <span className="inline-flex items-center gap-2">
      <span className={`h-2.5 w-2.5 rounded-full ${color}`} />
      {label}
    </span>
  );
}

function MiniLineChart({ value }) {
  const endY = Math.max(18, 72 - value * 0.5);

  return (
    <div className="relative h-20 overflow-hidden rounded border border-slate-200 bg-gradient-to-b from-slate-50 to-white">
      <div className="absolute inset-x-0 top-1/3 border-t border-slate-200" />
      <div className="absolute inset-x-0 top-2/3 border-t border-slate-200" />
      <svg className="absolute inset-0 h-full w-full" viewBox="0 0 320 80" preserveAspectRatio="none" aria-hidden="true">
        <path d={`M0 65 C 60 65, 90 55, 130 52 S 210 ${endY + 8}, 320 ${endY}`} fill="none" stroke="#005A83" strokeWidth="3" />
        <path d={`M0 80 L0 65 C 60 65, 90 55, 130 52 S 210 ${endY + 8}, 320 ${endY} L320 80 Z`} fill="#005A83" opacity="0.08" />
      </svg>
    </div>
  );
}

function VerticalComplianceBars({ value }) {
  const bars = [54, 72, 62, 80, 68, Math.max(10, value)];

  return (
    <div className="flex h-24 items-end gap-2">
      {bars.map((height, index) => (
        <div key={`${height}-${index}`} className="flex h-full w-3 items-end rounded-full bg-slate-200">
          <span
            className={`w-full rounded-full ${index >= bars.length - 2 ? "bg-[#E83F6F]" : "bg-[#32936F]"}`}
            style={{ height: `${height}%` }}
          />
        </div>
      ))}
    </div>
  );
}

function MiniBar({ label, value }) {
  return (
    <div className="grid grid-cols-[90px_1fr_42px] items-center gap-3 text-sm">
      <span className="text-slate-700">{label}</span>
      <span className="h-2 rounded-full bg-slate-200">
        <span className="block h-2 rounded-full bg-[#FFBF00]" style={{ width: `${value}%` }} />
      </span>
      <span className="text-right font-medium text-slate-700">{value}%</span>
    </div>
  );
}

function Sparkline() {
  return (
    <svg className="h-7 w-20" viewBox="0 0 80 28" aria-hidden="true">
      <path d="M2 22 L16 20 L28 16 L42 18 L56 10 L78 4" fill="none" stroke="#FFBF00" strokeWidth="2" />
    </svg>
  );
}

function QuickLink({ to, icon: Icon, label, detail }) {
  return (
    <Link to={to} className="rounded-lg border border-slate-200 bg-white p-4 transition hover:border-[#005A83] hover:bg-sky-50">
      <Icon className="h-5 w-5 text-[#005A83]" aria-hidden="true" />
      <p className="mt-3 text-sm font-semibold text-slate-900">{label}</p>
      <p className="mt-1 text-sm text-slate-600">{detail}</p>
    </Link>
  );
}

function InfoRow({ label, value }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <dt className="text-slate-500">{label}</dt>
      <dd className="font-medium text-slate-900">{value}</dd>
    </div>
  );
}
