import { ExternalLink, PlaneTakeoff } from "lucide-react";

import { Card, EmptyState, ErrorBanner, LoadingState, LockNotice, StatCard, StatusBadge } from "../../components/ui.jsx";
import { useApiResource } from "../../hooks/useAgentPortalData.js";
import AgentPageShell from "./AgentPageShell.jsx";

export default function SupplierAccessPage() {
  return (
    <AgentPageShell
      title="Supplier Access"
      description="Approved supplier portal details are shown only after final approval."
    >
      {() => <SupplierAccessContent />}
    </AgentPageShell>
  );
}

function SupplierAccessContent() {
  const suppliers = useApiResource("/supplier-access", {
    initialData: [],
    fallbackError: "Supplier access is locked until the agent is approved to trade.",
  });

  if (suppliers.loading) {
    return <LoadingState message="Loading supplier access..." />;
  }

  const rows = suppliers.data || [];

  return (
    <div className="space-y-6">
      {suppliers.error ? (
        <LockNotice title="Supplier access is locked" message="Agents only see supplier portals after admin has approved them to trade." />
      ) : (
        <ErrorBanner message={suppliers.error} />
      )}

      <div className="grid gap-4 md:grid-cols-3">
        <StatCard label="Visible suppliers" value={rows.length} detail="Unlocked supplier records" icon={PlaneTakeoff} />
        <StatCard label="Training required" value={rows.filter((item) => item.training_required).length} icon={PlaneTakeoff} />
        <StatCard label="Portal links" value={rows.filter((item) => item.portal_url).length} icon={ExternalLink} />
      </div>

      <Card title="Supplier Portals">
        {rows.length ? (
          <div className="grid gap-4 lg:grid-cols-2">
            {rows.map((supplier) => (
              <article key={supplier.id} className="rounded-lg border border-slate-200 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h2 className="text-sm font-semibold text-slate-950">{supplier.supplier_name}</h2>
                    <p className="mt-1 text-xs font-medium text-slate-500">{supplier.supplier_type}</p>
                  </div>
                  <StatusBadge status={supplier.training_required ? "Training Required" : "Available"} />
                </div>
                <p className="mt-3 whitespace-pre-wrap text-sm text-slate-600">{supplier.login_instructions || "Login instructions have not been added yet."}</p>
                {supplier.access_notes ? <p className="mt-3 text-sm text-slate-500">{supplier.access_notes}</p> : null}
                {supplier.portal_url ? (
                  <a className="mt-4 inline-flex items-center gap-2 rounded-lg border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50" href={supplier.portal_url} target="_blank" rel="noreferrer">
                    Open portal
                    <ExternalLink className="h-4 w-4" aria-hidden="true" />
                  </a>
                ) : null}
              </article>
            ))}
          </div>
        ) : (
          <EmptyState title="No supplier access yet" message="Supplier records appear here after final approval and admin publishing." />
        )}
      </Card>
    </div>
  );
}
