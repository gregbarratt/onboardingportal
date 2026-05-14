import { Download, FileUp, Search, Upload } from "lucide-react";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { apiClient } from "../../api/client.js";
import { Card, DataTable, ErrorBanner, LoadingState, PrimaryButton, SelectInput, StatusBadge, TextInput } from "../../components/ui.jsx";
import { useAuth } from "../../context/AuthContext.jsx";
import { buildAgentName, useAgents } from "../../hooks/useAdminData.js";
import { getFriendlyError } from "../../hooks/useAgentPortalData.js";
import { formatDate } from "../../utils/formatters.js";
import { agentStatuses } from "./adminConstants.js";
import AdminPageShell from "./AdminPageShell.jsx";

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
    } catch (err) {
      setImportError(getFriendlyError(err, "We could not import this CSV file."));
    } finally {
      setImporting(false);
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

        <Card
          title="Import Agents"
          description="Upload the completed CSV to create or update agent profiles, membership details, and Stripe IDs. If no organisation is named in the CSV, agents are added to your organisation. If Stripe sync is switched on, the portal will also pull live invoices and subscription status for imported Stripe customers."
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
              Sync live Stripe payments after import
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
                <ImportStat label="Stripe synced" value={importResult.stripe_synced} />
                <ImportStat label="Stripe issues" value={importResult.stripe_sync_failed} />
                <ImportStat label="Profiles enriched" value={importResult.stripe_profiles_synced} />
                <ImportStat label="Profile fields filled" value={importResult.stripe_profile_fields_synced} />
                <ImportStat label="Invoices synced" value={importResult.stripe_invoices_synced} />
                <ImportStat label="Subscriptions synced" value={importResult.stripe_subscriptions_synced} />
              </div>
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
                  Import completed with no row errors.
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

function ImportStat({ label, value }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-lg font-semibold text-slate-950">{value ?? 0}</p>
    </div>
  );
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
