import { Award, ExternalLink } from "lucide-react";

import { Card, DataTable, ErrorBanner, LoadingState, StatCard, StatusBadge } from "../../components/ui.jsx";
import { useAgentResource } from "../../hooks/useAgentPortalData.js";
import { formatDate } from "../../utils/formatters.js";
import AgentPageShell from "./AgentPageShell.jsx";

export default function CertificatesPage() {
  return (
    <AgentPageShell
      title="Certificates"
      description="Certificates prove completed training and show when a renewal is required."
    >
      {({ profile }) => <CertificatesContent profile={profile} />}
    </AgentPageShell>
  );
}

function CertificatesContent({ profile }) {
  const certificates = useAgentResource(profile, (id) => `/agents/${id}/certificates`, {
    initialData: [],
  });

  if (certificates.loading) {
    return <LoadingState message="Loading certificates..." />;
  }

  const rows = certificates.data || [];
  const activeCount = rows.filter((item) => item.status === "Active").length;
  const renewalCount = rows.filter((item) => item.renewal_required).length;

  return (
    <div className="space-y-6">
      <ErrorBanner message={certificates.error} />

      <div className="grid gap-4 md:grid-cols-3">
        <StatCard label="Total certificates" value={rows.length} icon={Award} />
        <StatCard label="Active certificates" value={activeCount} icon={Award} />
        <StatCard label="Renewals required" value={renewalCount} icon={Award} />
      </div>

      <Card title="Certificate Records">
        <DataTable
          rows={rows}
          emptyMessage="No certificates have been issued yet."
          columns={[
            { key: "certificate_name", label: "Certificate" },
            { key: "issued_date", label: "Issued", render: (row) => formatDate(row.issued_date) },
            { key: "expiry_date", label: "Expiry", render: (row) => formatDate(row.expiry_date) },
            { key: "renewal_required", label: "Renewal", render: (row) => (row.renewal_required ? "Required" : "Not required") },
            { key: "status", label: "Status", render: (row) => <StatusBadge status={row.status} /> },
            {
              key: "certificate_url",
              label: "File",
              render: (row) =>
                row.certificate_url ? (
                  <a className="inline-flex items-center gap-1 font-semibold text-sky-700 hover:text-sky-900" href={row.certificate_url} target="_blank" rel="noreferrer">
                    Open
                    <ExternalLink className="h-4 w-4" aria-hidden="true" />
                  </a>
                ) : (
                  "Not set"
                ),
            },
          ]}
        />
      </Card>
    </div>
  );
}
