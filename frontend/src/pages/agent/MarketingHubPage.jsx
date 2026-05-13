import { Download, ExternalLink, Megaphone } from "lucide-react";

import { Card, EmptyState, LoadingState, LockNotice, StatCard, StatusBadge } from "../../components/ui.jsx";
import { useApiResource } from "../../hooks/useAgentPortalData.js";
import AgentPageShell from "./AgentPageShell.jsx";

export default function MarketingHubPage() {
  return (
    <AgentPageShell
      title="Marketing Hub"
      description="Approved brand files, campaign assets, offer wording, and advertising guidance for agents."
    >
      {() => <MarketingContent />}
    </AgentPageShell>
  );
}

function MarketingContent() {
  const assets = useApiResource("/marketing-assets", {
    initialData: [],
    fallbackError: "Marketing access is locked until the social media and advertising policy is accepted.",
  });

  if (assets.loading) {
    return <LoadingState message="Loading marketing resources..." />;
  }

  const rows = assets.data || [];

  return (
    <div className="space-y-6">
      {assets.error ? (
        <LockNotice
          title="Marketing hub is locked"
          message="Agents only see marketing resources after accepting the social media and advertising policy."
        />
      ) : null}

      <div className="grid gap-4 md:grid-cols-3">
        <StatCard label="Marketing assets" value={rows.length} icon={Megaphone} />
        <StatCard label="Download files" value={rows.filter((item) => item.file_url).length} icon={Download} />
        <StatCard label="Resource links" value={rows.filter((item) => item.resource_url).length} icon={ExternalLink} />
      </div>

      <Card title="Approved Resources">
        {rows.length ? (
          <div className="grid gap-4 lg:grid-cols-2">
            {rows.map((asset) => (
              <article key={asset.id} className="rounded-lg border border-slate-200 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h2 className="text-sm font-semibold text-slate-950">{asset.asset_name}</h2>
                    <p className="mt-1 text-xs font-medium text-slate-500">{asset.asset_type}</p>
                  </div>
                  <StatusBadge status={asset.visible_to_agents ? "Visible" : "Hidden"} />
                </div>
                <p className="mt-3 text-sm text-slate-600">{asset.description || "No description added yet."}</p>
                {asset.approved_offer_wording ? (
                  <div className="mt-4 rounded-lg bg-slate-50 p-3 text-sm text-slate-700">
                    <p className="font-semibold text-slate-900">Approved wording</p>
                    <p className="mt-1">{asset.approved_offer_wording}</p>
                  </div>
                ) : null}
                <div className="mt-4 flex flex-wrap gap-2">
                  <AssetLink label="Download file" url={asset.file_url} icon={Download} />
                  <AssetLink label="Open resource" url={asset.resource_url} icon={ExternalLink} />
                </div>
              </article>
            ))}
          </div>
        ) : (
          <EmptyState title="No marketing assets yet" message={assets.error ? "Accept the required marketing policy to unlock this area." : "Admin can publish brand and campaign assets later."} />
        )}
      </Card>
    </div>
  );
}

function AssetLink({ label, url, icon: Icon }) {
  if (!url) return null;

  return (
    <a href={url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 rounded-lg border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50">
      <Icon className="h-4 w-4" aria-hidden="true" />
      {label}
    </a>
  );
}
