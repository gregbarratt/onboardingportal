import { BookMarked, LockKeyhole } from "lucide-react";

import { Card, EmptyState, ErrorBanner, LoadingState, LockNotice, StatCard, StatusBadge } from "../../components/ui.jsx";
import { useApiResource, useAgentResource } from "../../hooks/useAgentPortalData.js";
import AgentPageShell from "./AgentPageShell.jsx";

export default function FurtherTrainingPage() {
  return (
    <AgentPageShell
      title="Further Training"
      description="Optional and ongoing development modules become available after the mandatory onboarding training is complete."
    >
      {({ profile }) => <FurtherTrainingContent profile={profile} />}
    </AgentPageShell>
  );
}

function FurtherTrainingContent({ profile }) {
  const modules = useApiResource("/further-training", {
    initialData: [],
    fallbackError: "Further training is locked until mandatory onboarding training is complete.",
  });
  const progress = useAgentResource(profile, (id) => `/agents/${id}/further-training`, {
    initialData: [],
    fallbackError: "Further training progress is locked until mandatory onboarding training is complete.",
  });

  if (modules.loading || progress.loading) {
    return <LoadingState message="Loading further training..." />;
  }

  const locked = modules.error || progress.error;
  const moduleRows = modules.data || [];
  const progressRows = progress.data || [];
  const mandatoryCount = moduleRows.filter((item) => item.mandatory).length;

  return (
    <div className="space-y-6">
      {locked ? (
        <LockNotice
          title="Further training is locked"
          message="The backend only unlocks this area after required onboarding training is complete."
        />
      ) : (
        <ErrorBanner message={modules.error || progress.error} />
      )}

      <div className="grid gap-4 md:grid-cols-3">
        <StatCard label="Further modules" value={moduleRows.length} detail="Available after onboarding" icon={BookMarked} />
        <StatCard label="Mandatory extras" value={mandatoryCount} detail="Admin can require selected further training" icon={LockKeyhole} />
        <StatCard label="Progress records" value={progressRows.length} detail="Assigned development modules" icon={BookMarked} />
      </div>

      <Card title="Further Training Library">
        {moduleRows.length ? (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {moduleRows.map((module) => (
              <article key={module.id} className="rounded-lg border border-slate-200 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h2 className="text-sm font-semibold text-slate-950">{module.title}</h2>
                    <p className="mt-1 text-xs font-medium text-slate-500">{getCategoryName(module.category)}</p>
                  </div>
                  <StatusBadge status={module.mandatory ? "Mandatory" : "Optional"} />
                </div>
                <p className="mt-3 text-sm text-slate-600">{module.description || "No description added yet."}</p>
              </article>
            ))}
          </div>
        ) : (
          <EmptyState title="No further training yet" message={locked ? "Complete mandatory onboarding training to unlock this area." : "Admin can publish further training modules later."} />
        )}
      </Card>
    </div>
  );
}

function getCategoryName(category) {
  if (!category) return "Training";
  if (typeof category === "string") return category;
  return category.name || "Training";
}
