import { Check, ShieldCheck } from "lucide-react";
import { useState } from "react";

import { Card, DataTable, EmptyState, ErrorBanner, LoadingState, PrimaryButton, ProgressBar, StatCard, StatusBadge } from "../../components/ui.jsx";
import { apiClient } from "../../api/client.js";
import { useAuth } from "../../context/AuthContext.jsx";
import { getFriendlyError, useAgentResource, useApiResource } from "../../hooks/useAgentPortalData.js";
import { compactList, percentage } from "../../utils/formatters.js";
import AgentPageShell from "./AgentPageShell.jsx";

export default function ComplianceCentrePage() {
  return (
    <AgentPageShell
      title="Compliance Centre"
      description="View required policies, compliance status, customer money rules, advertising rules, and complaints guidance."
    >
      {({ profile }) => <ComplianceContent profile={profile} />}
    </AgentPageShell>
  );
}

function ComplianceContent({ profile }) {
  const { token } = useAuth();
  const policies = useApiResource("/compliance/policies", { initialData: [] });
  const status = useAgentResource(profile, (id) => `/agents/${id}/compliance-status`, {
    fallbackError: "Compliance status is not available yet.",
  });
  const [acceptingId, setAcceptingId] = useState(null);
  const [acceptError, setAcceptError] = useState("");
  const [acceptMessage, setAcceptMessage] = useState("");

  async function acceptPolicy(policyId) {
    setAcceptingId(policyId);
    setAcceptError("");
    setAcceptMessage("");

    try {
      await apiClient.post(`/compliance/policies/${policyId}/accept`, {}, token);
      await status.reload();
      setAcceptMessage("Policy accepted.");
    } catch (err) {
      setAcceptError(getFriendlyError(err, "We could not accept this policy."));
    } finally {
      setAcceptingId(null);
    }
  }

  if (policies.loading || status.loading) {
    return <LoadingState message="Loading compliance centre..." />;
  }

  const policyRows = policies.data || [];
  const compliance = status.data;
  const acceptedCount = compliance?.accepted_policy_count || 0;
  const requiredCount = compliance?.required_policy_count || policyRows.filter((item) => item.requires_acceptance).length;

  return (
    <div className="space-y-6">
      <ErrorBanner message={policies.error || status.error || acceptError} />
      {acceptMessage ? (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm font-medium text-emerald-700">
          {acceptMessage}
        </div>
      ) : null}

      <div className="grid gap-4 md:grid-cols-3">
        <StatCard label="Required policies" value={requiredCount} icon={ShieldCheck} />
        <StatCard label="Accepted policies" value={acceptedCount} icon={Check} />
        <StatCard label="Missing documents" value={compliance?.missing_document_types?.length || 0} icon={ShieldCheck} />
      </div>

      <Card title="Policy Acceptance Progress">
        <ProgressBar value={percentage(acceptedCount, requiredCount)} label={`${acceptedCount} of ${requiredCount} policies accepted`} />
      </Card>

      {compliance ? (
        <div className="grid gap-6 lg:grid-cols-2">
          <Card title="Compliance Checklist">
            {compliance.compliance_checklist?.length ? (
              <ul className="space-y-2 text-sm text-slate-700">
                {compliance.compliance_checklist.map((item) => (
                  <li key={item} className="rounded-lg border border-slate-200 p-3">
                    {item}
                  </li>
                ))}
              </ul>
            ) : (
              <EmptyState title="No checklist items" message="Compliance checklist items will appear here." />
            )}
          </Card>

          <Card title="Current Compliance Status">
            <dl className="space-y-3 text-sm">
              <StatusRow label="Agent status" value={<StatusBadge status={compliance.agent_status} />} />
              <StatusRow label="Compliance hold" value={compliance.compliance_hold ? "Yes" : "No"} />
              <StatusRow label="Missing policies" value={compactList(compliance.missing_policy_titles)} />
              <StatusRow label="Missing documents" value={compactList(compliance.missing_document_types)} />
              <StatusRow label="Rejected documents" value={compliance.rejected_documents?.length || 0} />
            </dl>
          </Card>
        </div>
      ) : null}

      <Card title="Policies to Accept">
        <DataTable
          rows={policyRows}
          emptyMessage="No compliance policies have been published yet."
          columns={[
            { key: "title", label: "Policy" },
            { key: "policy_type", label: "Type" },
            { key: "version", label: "Version" },
            { key: "requires_acceptance", label: "Required", render: (row) => (row.requires_acceptance ? "Yes" : "No") },
            {
              key: "action",
              label: "Action",
              render: (row) =>
                row.requires_acceptance ? (
                  <PrimaryButton type="button" icon={Check} disabled={acceptingId === row.id} onClick={() => acceptPolicy(row.id)}>
                    {acceptingId === row.id ? "Accepting..." : "Accept"}
                  </PrimaryButton>
                ) : (
                  "Read only"
                ),
            },
          ]}
        />
      </Card>

      {compliance ? (
        <div className="grid gap-6 lg:grid-cols-3">
          <GuidanceCard title="Customer Money Handling" items={compliance.customer_money_handling_rules} />
          <GuidanceCard title="Advertising & Social Media" items={compliance.advertising_and_social_media_rules} />
          <GuidanceCard title="Complaints Process" items={compliance.complaints_process} />
        </div>
      ) : null}
    </div>
  );
}

function StatusRow({ label, value }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <dt className="text-slate-500">{label}</dt>
      <dd className="font-medium text-slate-900">{value}</dd>
    </div>
  );
}

function GuidanceCard({ title, items }) {
  return (
    <Card title={title}>
      {items?.length ? (
        <ul className="space-y-2 text-sm text-slate-700">
          {items.map((item) => (
            <li key={item} className="rounded-lg bg-slate-50 p-3">
              {item}
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-slate-600">No guidance has been added yet.</p>
      )}
    </Card>
  );
}
