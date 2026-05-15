import { Check, Eye, FileText, ShieldCheck, X } from "lucide-react";
import { useState } from "react";

import { Card, DataTable, EmptyState, ErrorBanner, LoadingState, PrimaryButton, ProgressBar, SecondaryButton, StatCard, StatusBadge } from "../../components/ui.jsx";
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
  const [selectedPolicy, setSelectedPolicy] = useState(null);
  const [confirmRead, setConfirmRead] = useState(false);

  async function acceptPolicy(policyId) {
    if (!confirmRead) {
      setAcceptError("Please confirm you have opened and read the policy before accepting it.");
      return;
    }
    setAcceptingId(policyId);
    setAcceptError("");
    setAcceptMessage("");

    try {
      await apiClient.post(`/compliance/policies/${policyId}/accept`, {}, token);
      await status.reload();
      setAcceptMessage("Policy accepted.");
      setSelectedPolicy(null);
      setConfirmRead(false);
    } catch (err) {
      setAcceptError(getFriendlyError(err, "We could not accept this policy."));
    } finally {
      setAcceptingId(null);
    }
  }

  function openPolicy(policy) {
    setSelectedPolicy(policy);
    setConfirmRead(false);
    setAcceptError("");
  }

  if (policies.loading || status.loading) {
    return <LoadingState message="Loading compliance centre..." />;
  }

  const policyRows = policies.data || [];
  const compliance = status.data;
  const acceptedCount = compliance?.accepted_policy_count || 0;
  const requiredCount = compliance?.required_policy_count || policyRows.filter((item) => item.requires_acceptance).length;
  const acceptedPolicyIds = new Set(compliance?.accepted_policy_ids || []);
  const policiesToAccept = policyRows.filter((item) => item.requires_acceptance && !acceptedPolicyIds.has(item.id));
  const acceptedPolicies = policyRows.filter((item) => acceptedPolicyIds.has(item.id));

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

      <Card title="Policies to Accept" description="Open and read each policy before accepting it. Accepted policies move into the accepted list below.">
        <DataTable
          rows={policiesToAccept}
          emptyMessage="No policies are waiting for your acceptance."
          columns={[
            { key: "title", label: "Policy" },
            { key: "policy_type", label: "Type" },
            { key: "version", label: "Version" },
            { key: "requires_acceptance", label: "Required", render: (row) => (row.requires_acceptance ? "Yes" : "No") },
            {
              key: "action",
              label: "Action",
              render: (row) => (
                <PrimaryButton type="button" icon={Eye} onClick={() => openPolicy(row)}>
                  Read and accept
                </PrimaryButton>
              ),
            },
          ]}
        />
      </Card>

      <Card title="Accepted Policies">
        <DataTable
          rows={acceptedPolicies}
          emptyMessage="No policies have been accepted yet."
          columns={[
            { key: "title", label: "Policy" },
            { key: "policy_type", label: "Type" },
            { key: "version", label: "Version" },
            { key: "status", label: "Status", render: () => <StatusBadge status="Accepted" /> },
            {
              key: "action",
              label: "Action",
              render: (row) => (
                <SecondaryButton type="button" icon={FileText} onClick={() => openPolicy(row)}>
                  Read
                </SecondaryButton>
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

      {selectedPolicy ? (
        <PolicyModal
          policy={selectedPolicy}
          isAccepted={acceptedPolicyIds.has(selectedPolicy.id)}
          confirmRead={confirmRead}
          accepting={acceptingId === selectedPolicy.id}
          onConfirmChange={setConfirmRead}
          onAccept={() => acceptPolicy(selectedPolicy.id)}
          onClose={() => {
            setSelectedPolicy(null);
            setConfirmRead(false);
          }}
        />
      ) : null}
    </div>
  );
}

function PolicyModal({ policy, isAccepted, confirmRead, accepting, onConfirmChange, onAccept, onClose }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4">
      <div className="flex max-h-[90vh] w-full max-w-4xl flex-col rounded-lg bg-white shadow-xl">
        <div className="flex items-start justify-between gap-4 border-b border-slate-200 p-5">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-sky-700">Compliance policy</p>
            <h2 className="mt-1 text-xl font-semibold text-slate-950">{policy.title}</h2>
            <p className="mt-1 text-sm text-slate-600">
              {policy.policy_type} | Version {policy.version}
            </p>
          </div>
          <button type="button" className="rounded-lg p-2 text-slate-500 hover:bg-slate-100" onClick={onClose} aria-label="Close policy">
            <X className="h-5 w-5" aria-hidden="true" />
          </button>
        </div>
        <div className="overflow-y-auto p-5">
          <div className="whitespace-pre-wrap rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm leading-6 text-slate-800">
            {policy.content}
          </div>
          {isAccepted ? (
            <div className="mt-4 rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm font-medium text-emerald-700">
              You have accepted this policy.
            </div>
          ) : (
            <label className="mt-4 flex gap-3 rounded-lg border border-slate-200 p-4 text-sm text-slate-700">
              <input type="checkbox" checked={confirmRead} onChange={(event) => onConfirmChange(event.target.checked)} />
              <span>I confirm that I have opened, read, understood, and accept this policy.</span>
            </label>
          )}
        </div>
        <div className="flex flex-wrap justify-end gap-3 border-t border-slate-200 p-5">
          <SecondaryButton type="button" icon={X} onClick={onClose}>
            Close
          </SecondaryButton>
          {!isAccepted ? (
            <PrimaryButton type="button" icon={Check} disabled={!confirmRead || accepting} onClick={onAccept}>
              {accepting ? "Accepting..." : "Accept policy"}
            </PrimaryButton>
          ) : null}
        </div>
      </div>
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
