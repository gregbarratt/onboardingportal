import { Link } from "react-router-dom";

import { Card, EmptyState, ErrorBanner, LoadingState, PageHeader } from "../../components/ui.jsx";
import { useAgentProfile } from "../../hooks/useAgentPortalData.js";

export default function AgentPageShell({ eyebrow = "Agent portal", title, description, children, requireProfile = true }) {
  const agentProfile = useAgentProfile();
  const { profile, loading, error } = agentProfile;

  if (loading) {
    return (
      <div className="space-y-6">
        <PageHeader eyebrow={eyebrow} title={title} description={description} />
        <LoadingState message="Loading your agent area..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <PageHeader eyebrow={eyebrow} title={title} description={description} />
        <ErrorBanner message={error} />
      </div>
    );
  }

  if (requireProfile && !profile) {
    return (
      <div className="space-y-6">
        <PageHeader eyebrow={eyebrow} title={title} description={description} />
        <Card>
          <EmptyState
            title="Create your agent profile first"
            message="Your profile connects your account to the onboarding checklist, payments, training, and documents."
          />
          <div className="mt-4 flex justify-center">
            <Link
              to="/profile"
              className="inline-flex items-center justify-center rounded-lg bg-sky-700 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-sky-800"
            >
              Go to My Profile
            </Link>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader eyebrow={eyebrow} title={title} description={description} />
      {children(agentProfile)}
    </div>
  );
}
