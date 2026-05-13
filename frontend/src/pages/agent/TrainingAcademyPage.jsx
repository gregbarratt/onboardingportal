import { BookOpenCheck, Clock, GraduationCap } from "lucide-react";
import { Link } from "react-router-dom";

import { Card, EmptyState, ErrorBanner, LoadingState, ProgressBar, StatCard, StatusBadge } from "../../components/ui.jsx";
import { useApiResource, useAgentResource } from "../../hooks/useAgentPortalData.js";
import { percentage } from "../../utils/formatters.js";
import AgentPageShell from "./AgentPageShell.jsx";

export default function TrainingAcademyPage() {
  return (
    <AgentPageShell
      title="Training Academy"
      description="Complete the required lessons for onboarding, then continue learning with extra modules later."
    >
      {({ profile }) => <TrainingContent profile={profile} />}
    </AgentPageShell>
  );
}

function TrainingContent({ profile }) {
  const modules = useApiResource("/training/modules", { initialData: [] });
  const progress = useAgentResource(profile, (id) => `/agents/${id}/training`, {
    initialData: [],
  });

  if (modules.loading || progress.loading) {
    return <LoadingState message="Loading training academy..." />;
  }

  const progressRows = progress.data || [];
  const moduleRows = (modules.data || []).filter((item) => item.training_track === "Onboarding");
  const mandatoryModules = moduleRows.filter((item) => item.mandatory);
  const completedMandatory = progressRows.filter((item) => item.training_module?.mandatory && item.progress_status === "Complete").length;
  const completedAll = progressRows.filter((item) => item.progress_status === "Complete").length;
  const progressByModule = new Map(progressRows.map((item) => [item.training_module_id, item]));
  const estimatedMinutes = moduleRows.reduce((total, item) => total + readEstimatedMinutes(item.estimated_completion_time), 0);

  return (
    <div className="space-y-6">
      <ErrorBanner message={modules.error || progress.error} />

      <div className="grid gap-4 md:grid-cols-3">
        <StatCard label="Mandatory modules" value={mandatoryModules.length} detail="Required before approval" icon={GraduationCap} />
        <StatCard label="Completed" value={completedAll} detail="Training records complete" icon={BookOpenCheck} />
        <StatCard label="Estimated time" value={`${estimatedMinutes} mins`} icon={Clock} />
      </div>

      <Card title="Mandatory Training Progress">
        <ProgressBar value={percentage(completedMandatory, mandatoryModules.length)} label={`${completedMandatory} of ${mandatoryModules.length} mandatory modules complete`} />
      </Card>

      <Card title="Training Modules" description="Open a module to view the embedded lesson files, written content, and quiz requirements.">
        {moduleRows.length ? (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {moduleRows.map((module) => {
              const rowProgress = progressByModule.get(module.id);

              return (
                <Link key={module.id} to={`/training/${module.id}`} className="rounded-lg border border-slate-200 p-4 transition hover:border-sky-300 hover:bg-sky-50">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-slate-950">{module.title}</p>
                      <p className="mt-1 text-xs font-medium text-slate-500">{getCategoryName(module.category)}</p>
                    </div>
                    <StatusBadge status={rowProgress?.progress_status || (module.mandatory ? "Mandatory" : "Optional")} />
                  </div>
                  <p className="mt-3 text-sm text-slate-600">{module.description || "No description added yet."}</p>
                  <div className="mt-4 flex flex-wrap gap-2 text-xs text-slate-500">
                    <span>{module.estimated_completion_time || "Not timed"}</span>
                    <span>{module.quiz_required ? `Pass mark ${module.pass_mark || 0}%` : "No quiz"}</span>
                  </div>
                </Link>
              );
            })}
          </div>
        ) : (
          <EmptyState title="No modules yet" message="Training modules will appear when admin publishes them." />
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

function readEstimatedMinutes(value) {
  if (typeof value === "number") return value;
  if (!value) return 0;
  const match = String(value).match(/\d+/);
  return match ? Number(match[0]) : 0;
}
