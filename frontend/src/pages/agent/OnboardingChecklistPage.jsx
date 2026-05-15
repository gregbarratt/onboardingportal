import { Link } from "react-router-dom";

import {
  Card,
  DataTable,
  ErrorBanner,
  LoadingState,
  ProgressBar,
  StatusBadge,
} from "../../components/ui.jsx";
import { useAgentResource } from "../../hooks/useAgentPortalData.js";
import { formatDate, percentage } from "../../utils/formatters.js";
import AgentPageShell from "./AgentPageShell.jsx";

function EvidenceLink({ value }) {
  if (!value) return "Not set";

  return (
    <a className="font-semibold text-sky-700 hover:text-sky-900" href={value} target="_blank" rel="noreferrer">
      Open evidence
    </a>
  );
}

const onboardingActionLinks = {
  "Complete personal profile": "/profile",
  "Upload ID document": "/documents",
  "Upload proof of address": "/documents",
  "Add bank details for commission payments": "/profile",
  "Sign contractor agreement": "/documents",
  "Accept membership terms": "/membership",
  "Complete final assessment": "/training",
};

function getOnboardingAction(stepTitle) {
  if (stepTitle === "Admin final approval") {
    return {
      label: "Waiting for admin",
      to: null,
    };
  }

  return {
    label: "Select",
    to: onboardingActionLinks[stepTitle] || "/dashboard",
  };
}

export default function OnboardingChecklistPage() {
  return (
    <AgentPageShell
      title="Onboarding Checklist"
      description="This checklist shows the steps that must be completed before an agent can be approved to trade."
    >
      {({ profile }) => <OnboardingContent profile={profile} />}
    </AgentPageShell>
  );
}

function OnboardingContent({ profile }) {
  const progress = useAgentResource(profile, (id) => `/agents/${id}/onboarding`, {
    initialData: [],
  });

  const rows = progress.data || [];
  const completedCount = rows.filter((item) => item.completion_status === "Complete").length;

  if (progress.loading) {
    return <LoadingState message="Loading onboarding checklist..." />;
  }

  return (
    <div className="space-y-6">
      <ErrorBanner message={progress.error} />

      <Card title="Checklist Progress" description="Use Select to open the area where each step is completed. Admin will approve items that need checking.">
        <ProgressBar value={percentage(completedCount, rows.length)} label={`${completedCount} of ${rows.length} steps complete`} />
      </Card>

      <Card title="Checklist Items">
        <DataTable
          rows={rows}
          emptyMessage="No onboarding checklist steps have been assigned yet."
          columns={[
            { key: "title", label: "Step", render: (row) => row.step?.title || "Untitled step" },
            { key: "required", label: "Required", render: (row) => (row.step?.required ? "Yes" : "No") },
            { key: "completion_status", label: "Status", render: (row) => <StatusBadge status={row.completion_status} /> },
            { key: "due_date", label: "Due", render: (row) => formatDate(row.due_date) },
            { key: "evidence_file_or_link", label: "Evidence", render: (row) => <EvidenceLink value={row.evidence_file_or_link} /> },
            { key: "approved_date", label: "Approved", render: (row) => formatDate(row.approved_date) },
            {
              key: "action",
              label: "Action",
              render: (row) => {
                const action = getOnboardingAction(row.step?.title);
                if (!action.to) {
                  return <span className="font-semibold text-slate-500">{action.label}</span>;
                }

                return (
                  <Link className="font-semibold text-sky-700 hover:text-sky-900" to={action.to}>
                    {action.label}
                  </Link>
                );
              },
            },
          ]}
        />
      </Card>
    </div>
  );
}
