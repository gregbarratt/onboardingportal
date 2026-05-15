import { Download, FileUp, Save, Search, Upload, UserPlus, X } from "lucide-react";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { apiClient } from "../../api/client.js";
import {
  Card,
  DataTable,
  ErrorBanner,
  FormField,
  LoadingState,
  PrimaryButton,
  SecondaryButton,
  SelectInput,
  StatusBadge,
  TextArea,
  TextInput,
} from "../../components/ui.jsx";
import { useAuth } from "../../context/AuthContext.jsx";
import { buildAgentName, useAgents } from "../../hooks/useAdminData.js";
import { getFriendlyError } from "../../hooks/useAgentPortalData.js";
import { formatDate } from "../../utils/formatters.js";
import { agentStatuses } from "./adminConstants.js";
import AdminPageShell from "./AdminPageShell.jsx";

const emptyManualAgentForm = {
  first_name: "",
  last_name: "",
  email: "",
  personal_email: "",
  company_email: "",
  phone: "",
  business_name: "",
  agent_id: "",
  status: "Registered",
  joining_date: "",
  address: "",
  postcode: "",
  portal_access_enabled: true,
  send_password_reset_email: true,
};

export default function AdminAgentListPage() {
  const { token } = useAuth();
  const agents = useAgents();
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("All");
  const [importFile, setImportFile] = useState(null);
  const [importing, setImporting] = useState(false);
  const [importError, setImportError] = useState("");
  const [importResult, setImportResult] = useState(null);
  const [syncStripeAfterImport, setSyncStripeAfterImport] = useState(true);
  const [stripeSyncing, setStripeSyncing] = useState(false);
  const [showManualForm, setShowManualForm] = useState(false);
  const [manualForm, setManualForm] = useState(emptyManualAgentForm);
  const [manualSaving, setManualSaving] = useState(false);
  const [manualError, setManualError] = useState("");
  const [manualMessage, setManualMessage] = useState("");

  const filteredAgents = useMemo(() => {
    const query = search.trim().toLowerCase();

    return (agents.data || []).filter((agent) => {
      const matchesStatus = status === "All" || agent.status === status;
      const searchable = `${buildAgentName(agent)} ${agent.email} ${agent.business_name || ""} ${agent.agent_id || ""}`.toLowerCase();
      return matchesStatus && (!query || searchable.includes(query));
    });
  }, [agents.data, search, status]);

  async function handleImport(event) {
    event.preventDefault();
    if (!importFile) {
      setImportError("Choose a CSV file first.");
      return;
    }

    setImporting(true);
    setImportError("");
    setImportResult(null);

    try {
      const fileContentBase64 = await readFileAsBase64(importFile);
      const result = await apiClient.post(
        "/agents/import/csv",
        {
          file_name: importFile.name,
          file_content_base64: fileContentBase64,
          update_existing: true,
          sync_stripe_after_import: syncStripeAfterImport,
        },
        token,
      );
      setImportResult(result);
      await agents.reload();
      if (syncStripeAfterImport && result.stripe_sync_agent_ids?.length) {
        void runStripeSyncBatches(result);
      }
    } catch (err) {
      setImportError(getFriendlyError(err, "We could not import this CSV file."));
    } finally {
      setImporting(false);
    }
  }

  function updateManualForm(field, value) {
    setManualForm((current) => ({ ...current, [field]: value }));
  }

  async function handleManualCreate(event) {
    event.preventDefault();
    setManualSaving(true);
    setManualError("");
    setManualMessage("");

    try {
      const result = await apiClient.post("/agents/manual", cleanManualAgentPayload(manualForm), token);
      setManualMessage(result.message || "Agent created.");
      setManualForm(emptyManualAgentForm);
      setShowManualForm(false);
      await agents.reload();
    } catch (err) {
      setManualError(getFriendlyError(err, "We could not create this agent."));
    } finally {
      setManualSaving(false);
    }
  }

  async function runStripeSyncBatches(startResult) {
    const agentIds = startResult.stripe_sync_agent_ids || [];
    if (!agentIds.length) return;

    setStripeSyncing(true);
    let afterAgentId = null;
    let totals = { ...startResult };

    try {
      while (true) {
        const batch = await apiClient.post(
          "/agents/stripe/import-sync-batch",
          {
            agent_profile_ids: agentIds,
            after_agent_id: afterAgentId,
            limit: 1,
          },
          token,
        );

        totals = mergeStripeBatchResult(totals, batch);
        afterAgentId = batch.next_after_agent_id;
        setImportResult(totals);

        if (batch.done || !batch.has_more || !afterAgentId) break;
        await wait(300);
      }
      await agents.reload();
    } catch (err) {
      setImportError(getFriendlyError(err, "The agents imported, but the Stripe refresh stopped."));
    } finally {
      setStripeSyncing(false);
    }
  }

  if (agents.loading) {
    return (
      <AdminPageShell title="Agent List" description="Find and manage agent records.">
        <LoadingState message="Loading agents..." />
      </AdminPageShell>
    );
  }

  return (
    <AdminPageShell title="Agent List" description="Search agents, check their status, and open their full admin record.">
      <div className="space-y-6">
        <ErrorBanner message={agents.error} />
        <ErrorBanner message={importError} />
        <ErrorBanner message={manualError} />

        {manualMessage ? (
          <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm font-medium text-emerald-700">
            {manualMessage}
          </div>
        ) : null}

        <Card
          title="Add Agent Manually"
          description="Create one agent at a time. This creates their portal login, agent profile, and starter membership record."
          actions={
            showManualForm ? (
              <SecondaryButton type="button" icon={X} onClick={() => setShowManualForm(false)}>
                Close form
              </SecondaryButton>
            ) : (
              <PrimaryButton type="button" icon={UserPlus} onClick={() => setShowManualForm(true)}>
                Add agent
              </PrimaryButton>
            )
          }
        >
          {showManualForm ? (
            <form onSubmit={handleManualCreate} className="space-y-5">
              <div className="grid gap-4 md:grid-cols-2">
                <FormField label="First name">
                  <TextInput value={manualForm.first_name} onChange={(event) => updateManualForm("first_name", event.target.value)} required />
                </FormField>
                <FormField label="Last name">
                  <TextInput value={manualForm.last_name} onChange={(event) => updateManualForm("last_name", event.target.value)} required />
                </FormField>
                <FormField label="Login email" help="This is the email address they use to sign in.">
                  <TextInput type="email" value={manualForm.email} onChange={(event) => updateManualForm("email", event.target.value)} required />
                </FormField>
                <FormField label="Personal email" help="Optional. Use this if their personal email is different.">
                  <TextInput type="email" value={manualForm.personal_email} onChange={(event) => updateManualForm("personal_email", event.target.value)} />
                </FormField>
                <FormField label="Company email" help="Optional One Travel Club email if they have one.">
                  <TextInput type="email" value={manualForm.company_email} onChange={(event) => updateManualForm("company_email", event.target.value)} />
                </FormField>
                <FormField label="Mobile number">
                  <TextInput value={manualForm.phone} onChange={(event) => updateManualForm("phone", event.target.value)} />
                </FormField>
                <FormField label="Business name">
                  <TextInput value={manualForm.business_name} onChange={(event) => updateManualForm("business_name", event.target.value)} />
                </FormField>
                <FormField label="Agent ID" help="Optional. Leave blank and the portal will choose the next ID.">
                  <TextInput value={manualForm.agent_id} onChange={(event) => updateManualForm("agent_id", event.target.value)} placeholder="Example: OTC-00134" />
                </FormField>
                <FormField label="Status">
                  <SelectInput value={manualForm.status} onChange={(event) => updateManualForm("status", event.target.value)}>
                    {agentStatuses.map((item) => (
                      <option key={item} value={item}>
                        {item}
                      </option>
                    ))}
                  </SelectInput>
                </FormField>
                <FormField label="Joining date">
                  <TextInput type="date" value={manualForm.joining_date} onChange={(event) => updateManualForm("joining_date", event.target.value)} />
                </FormField>
                <FormField label="Postcode">
                  <TextInput value={manualForm.postcode} onChange={(event) => updateManualForm("postcode", event.target.value)} />
                </FormField>
              </div>
              <FormField label="Address">
                <TextArea value={manualForm.address} onChange={(event) => updateManualForm("address", event.target.value)} />
              </FormField>
              <div className="grid gap-3 md:grid-cols-2">
                <label className="flex items-center gap-3 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-medium text-slate-700">
                  <input
                    type="checkbox"
                    checked={manualForm.portal_access_enabled}
                    onChange={(event) => updateManualForm("portal_access_enabled", event.target.checked)}
                    className="h-4 w-4 rounded border-slate-300 text-teal-700 focus:ring-teal-700"
                  />
                  Give this agent portal access
                </label>
                <label className="flex items-center gap-3 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-medium text-slate-700">
                  <input
                    type="checkbox"
                    checked={manualForm.send_password_reset_email}
                    onChange={(event) => updateManualForm("send_password_reset_email", event.target.checked)}
                    className="h-4 w-4 rounded border-slate-300 text-teal-700 focus:ring-teal-700"
                  />
                  Send password setup email
                </label>
              </div>
              <div className="flex flex-wrap gap-2">
                <PrimaryButton type="submit" icon={Save} disabled={manualSaving}>
                  {manualSaving ? "Creating agent..." : "Create agent"}
                </PrimaryButton>
                <SecondaryButton type="button" icon={X} onClick={() => setShowManualForm(false)} disabled={manualSaving}>
                  Cancel
                </SecondaryButton>
              </div>
            </form>
          ) : (
            <p className="text-sm text-slate-600">
              Use this for one-off agents. For a large list, keep using the CSV importer below.
            </p>
          )}
        </Card>

        <Card
          title="Import Agents"
          description="Upload the completed CSV to create or update agent profiles, membership details, and Stripe IDs. If no organisation is named in the CSV, agents are added to your organisation. If Stripe refresh is switched on, the portal saves the import first, then refreshes Stripe in small batches while this page stays open."
          actions={
            <a
              className="inline-flex items-center justify-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50"
              href="/templates/agent_import_template.csv"
              download
            >
              <Download className="h-4 w-4" aria-hidden="true" />
              Download CSV
            </a>
          }
        >
          <form onSubmit={handleImport} className="grid gap-4 lg:grid-cols-[1fr_auto] lg:items-end">
            <label className="block">
              <span className="text-sm font-medium text-slate-700">Completed CSV file</span>
              <input
                type="file"
                accept=".csv,text/csv"
                onChange={(event) => setImportFile(event.target.files?.[0] || null)}
                className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 shadow-sm file:mr-4 file:rounded-md file:border-0 file:bg-sky-50 file:px-3 file:py-1.5 file:text-sm file:font-semibold file:text-sky-700 hover:file:bg-sky-100"
              />
            </label>
            <label className="flex items-center gap-3 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-medium text-slate-700 lg:col-span-2">
              <input
                type="checkbox"
                checked={syncStripeAfterImport}
                onChange={(event) => setSyncStripeAfterImport(event.target.checked)}
                className="h-4 w-4 rounded border-slate-300 text-teal-700 focus:ring-teal-700"
              />
              Refresh live Stripe payments after import
            </label>
            <PrimaryButton type="submit" icon={importing ? FileUp : Upload} disabled={importing}>
              {importing ? "Importing..." : "Import agents"}
            </PrimaryButton>
          </form>

          {importResult ? (
            <div className="mt-5 space-y-4">
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
                <ImportStat label="Rows" value={importResult.total_rows} />
                <ImportStat label="Created" value={importResult.created} />
                <ImportStat label="Updated" value={importResult.updated} />
                <ImportStat label="Skipped" value={importResult.skipped} />
                <ImportStat label="Next ID" value={importResult.next_agent_id} />
                <ImportStat label="Stripe queued" value={importResult.stripe_sync_queued} />
                <ImportStat label="Stripe synced" value={importResult.stripe_synced} />
                <ImportStat label="Stripe issues" value={importResult.stripe_sync_failed} />
                <ImportStat label="Profiles enriched" value={importResult.stripe_profiles_synced} />
                <ImportStat label="Profile fields filled" value={importResult.stripe_profile_fields_synced} />
                <ImportStat label="Invoices synced" value={importResult.stripe_invoices_synced} />
                <ImportStat label="Subscriptions synced" value={importResult.stripe_subscriptions_synced} />
              </div>
              {stripeSyncing ? (
                <div className="rounded-lg border border-sky-200 bg-sky-50 p-4 text-sm font-medium text-sky-800">
                  Stripe payment refresh is running in small batches. You can stay on this page while the numbers update.
                </div>
              ) : null}
              {importResult.errors?.length ? (
                <DataTable
                  rows={importResult.errors}
                  emptyMessage="No import errors."
                  columns={[
                    { key: "row_number", label: "Row" },
                    { key: "identifier", label: "Agent" },
                    { key: "message", label: "Issue" },
                  ]}
                />
              ) : (
                <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm font-medium text-emerald-700">
                  Import completed with no row errors. Stripe payment data refreshes in small batches where queued.
                </div>
              )}
            </div>
          ) : null}
        </Card>

        <Card title="Filters">
          <div className="grid gap-4 md:grid-cols-[1fr_260px]">
            <label className="block">
              <span className="text-sm font-medium text-slate-700">Search</span>
              <div className="relative mt-1">
                <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" aria-hidden="true" />
                <TextInput className="pl-9" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Name, email, business, or agent ID" />
              </div>
            </label>
            <label className="block">
              <span className="text-sm font-medium text-slate-700">Status</span>
              <SelectInput value={status} onChange={(event) => setStatus(event.target.value)}>
                <option value="All">All statuses</option>
                {agentStatuses.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </SelectInput>
            </label>
          </div>
        </Card>

        <Card title="Agents" description={`${filteredAgents.length} agent records shown.`}>
          <DataTable
            rows={filteredAgents}
            emptyMessage="No agents match these filters."
            columns={[
              {
                key: "name",
                label: "Agent",
                render: (row) => (
                  <div>
                    <Link className="font-semibold text-sky-700 hover:text-sky-900" to={`/admin/agents/${row.id}`}>
                      {buildAgentName(row)}
                    </Link>
                    <p className="text-xs text-slate-500">{row.email}</p>
                  </div>
                ),
              },
              { key: "agent_id", label: "Agent ID" },
              { key: "business_name", label: "Business" },
              { key: "status", label: "Status", render: (row) => <StatusBadge status={row.status} /> },
              { key: "joining_date", label: "Joining date", render: (row) => formatDate(row.joining_date) },
              {
                key: "actions",
                label: "Actions",
                render: (row) => (
                  <div className="flex flex-wrap gap-2">
                    <Link className="font-semibold text-sky-700 hover:text-sky-900" to={`/admin/agents/${row.id}`}>
                      Details
                    </Link>
                    <Link className="font-semibold text-sky-700 hover:text-sky-900" to={`/admin/agents/${row.id}/membership`}>
                      Payments
                    </Link>
                  </div>
                ),
              },
            ]}
          />
        </Card>
      </div>
    </AdminPageShell>
  );
}

function cleanManualAgentPayload(form) {
  const payload = {
    ...form,
    joining_date: form.joining_date || null,
  };

  Object.keys(payload).forEach((key) => {
    if (typeof payload[key] === "string") {
      const cleaned = payload[key].trim();
      payload[key] = cleaned || null;
    }
  });

  return payload;
}

function ImportStat({ label, value }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-lg font-semibold text-slate-950">{value ?? 0}</p>
    </div>
  );
}

const stripeResultKeys = [
  "stripe_synced",
  "stripe_sync_failed",
  "stripe_profiles_synced",
  "stripe_profile_fields_synced",
  "stripe_invoices_synced",
  "stripe_subscriptions_synced",
];

function mergeStripeBatchResult(importResult, batch) {
  const next = { ...importResult };
  stripeResultKeys.forEach((key) => {
    next[key] = (next[key] || 0) + (batch[key] || 0);
  });
  const batchErrors = (batch.errors || []).map((error) => ({
    row_number: "Stripe",
    identifier: error.identifier || `Agent ${error.agent_id}`,
    message: error.message,
  }));
  next.errors = [...(next.errors || []), ...batchErrors];
  return next;
}

function wait(milliseconds) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, milliseconds);
  });
}

function readFileAsBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = String(reader.result || "");
      resolve(result.split(",", 2)[1] || result);
    };
    reader.onerror = () => reject(new Error("The file could not be read."));
    reader.readAsDataURL(file);
  });
}
