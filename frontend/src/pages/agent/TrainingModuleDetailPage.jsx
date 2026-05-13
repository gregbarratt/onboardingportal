import { ArrowLeft, ExternalLink } from "lucide-react";
import { Link, useParams } from "react-router-dom";

import { Card, ErrorBanner, LoadingState, PageHeader, StatusBadge } from "../../components/ui.jsx";
import { useApiResource } from "../../hooks/useAgentPortalData.js";

export default function TrainingModuleDetailPage() {
  const { moduleId } = useParams();
  const module = useApiResource(`/training/modules/${moduleId}`, {
    fallbackError: "We could not load this training module.",
  });

  if (module.loading) {
    return (
      <div className="space-y-6">
        <PageHeader title="Training Module" description="Loading the lesson content." />
        <LoadingState message="Loading training module..." />
      </div>
    );
  }

  const data = module.data;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Training Academy"
        title={data?.title || "Training Module"}
        description={data?.description || "View this training lesson and any attached resources."}
        actions={
          <Link className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50" to="/training">
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
            Back to training
          </Link>
        }
      />

      <ErrorBanner message={module.error} />

      {data ? (
        <>
          <div className="grid gap-4 md:grid-cols-4">
            <Card title="Category">
              <p className="text-sm font-medium text-slate-900">{getCategoryName(data.category)}</p>
            </Card>
            <Card title="Level">
              <p className="text-sm font-medium text-slate-900">{data.level || "Not set"}</p>
            </Card>
            <Card title="Status">
              <StatusBadge status={data.published_status} />
            </Card>
            <Card title="Quiz">
              <p className="text-sm font-medium text-slate-900">{data.quiz_required ? `Required, pass mark ${data.pass_mark || 0}%` : "Not required"}</p>
            </Card>
          </div>

          <Card title="Lesson Content">
            {data.text_content ? (
              <div className="whitespace-pre-wrap text-sm leading-6 text-slate-700">{data.text_content}</div>
            ) : (
              <p className="text-sm text-slate-600">No written content has been added yet.</p>
            )}
          </Card>

          <Card title="Resources">
            <div className="grid gap-3 sm:grid-cols-3">
              <ResourceLink label="Content link" url={data.content_url} />
              <ResourceLink label="Video" url={data.video_url} />
              <ResourceLink label="PDF" url={data.pdf_url} />
            </div>
          </Card>
        </>
      ) : null}
    </div>
  );
}

function getCategoryName(category) {
  if (!category) return "Training";
  if (typeof category === "string") return category;
  return category.name || "Training";
}

function ResourceLink({ label, url }) {
  if (!url) {
    return <div className="rounded-lg border border-slate-200 p-4 text-sm text-slate-500">{label}: Not added</div>;
  }

  return (
    <a href={url} target="_blank" rel="noreferrer" className="flex items-center justify-between gap-3 rounded-lg border border-slate-200 p-4 text-sm font-semibold text-sky-700 hover:bg-sky-50">
      {label}
      <ExternalLink className="h-4 w-4" aria-hidden="true" />
    </a>
  );
}
