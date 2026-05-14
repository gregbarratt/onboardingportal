import { Building2, Plus } from "lucide-react";
import { useMemo, useState } from "react";

import { apiClient } from "../../api/client.js";
import {
  Card,
  DataTable,
  ErrorBanner,
  FormField,
  LoadingState,
  PrimaryButton,
  StatusBadge,
  TextArea,
  TextInput,
} from "../../components/ui.jsx";
import { useAuth } from "../../context/AuthContext.jsx";
import { getFriendlyError, useApiResource } from "../../hooks/useAgentPortalData.js";
import AdminPageShell from "./AdminPageShell.jsx";

const emptyOrganizationForm = {
  name: "",
  slug: "",
  contact_email: "",
  notes: "",
};

export default function AdminSettingsPage() {
  const { token, user } = useAuth();
  const organizations = useApiResource("/organizations", {
    fallbackError: "We could not load organisations.",
    initialData: [],
  });
  const [form, setForm] = useState(emptyOrganizationForm);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState("");

  const isSuperAdmin = user?.role?.name === "Super Admin";
  const currentOrganization = useMemo(() => {
    if (user?.organization) return user.organization;
    return organizations.data?.find((item) => item.id === user?.organization_id) || null;
  }, [organizations.data, user]);

  async function handleCreateOrganization(event) {
    event.preventDefault();
    setSaving(true);
    setSaveError("");

    try {
      await apiClient.post(
        "/organizations",
        {
          name: form.name,
          slug: form.slug || null,
          contact_email: form.contact_email || null,
          notes: form.notes || null,
          status: "Active",
        },
        token,
      );
      setForm(emptyOrganizationForm);
      await organizations.reload();
    } catch (err) {
      setSaveError(getFriendlyError(err, "Organisation could not be created."));
    } finally {
      setSaving(false);
    }
  }

  if (organizations.loading) {
    return (
      <AdminPageShell title="Settings" description="Manage portal rules and organisation access.">
        <LoadingState message="Loading settings..." />
      </AdminPageShell>
    );
  }

  return (
    <AdminPageShell title="Settings" description="Manage portal rules and organisation access.">
      <div className="space-y-6">
        <ErrorBanner message={organizations.error} />
        <ErrorBanner message={saveError} />

        <div className="grid gap-6 xl:grid-cols-2">
          <Card title="Current Organisation" description="This controls which company records this user can work with.">
            <div className="flex items-start gap-4">
              <span className="rounded-lg bg-sky-50 p-3 text-sky-700">
                <Building2 className="h-6 w-6" aria-hidden="true" />
              </span>
              <div className="space-y-2 text-sm">
                <p className="text-lg font-semibold text-slate-950">{currentOrganization?.name || "Not set"}</p>
                <p className="text-slate-600">Role: {user?.role?.name || "User"}</p>
                <p className="text-slate-600">Organisation key: {currentOrganization?.slug || "Not set"}</p>
                <StatusBadge status={currentOrganization?.status || "Not set"} />
              </div>
            </div>
          </Card>

          <Card title="Portal Access Rules">
            <dl className="space-y-4 text-sm">
              <Rule label="Super Admin" value="Can see every organisation and every agent." />
              <Rule label="Organisation Admin" value="Can manage one organisation and its agents." />
              <Rule label="Admin roles" value="Stay inside their own organisation." />
              <Rule label="Agents" value="Only see their own portal record." />
            </dl>
          </Card>
        </div>

        {isSuperAdmin ? (
          <Card title="Create Organisation" description="Add another company if you later allow other brands or partners to use this portal.">
            <form onSubmit={handleCreateOrganization} className="grid gap-4 lg:grid-cols-2">
              <FormField label="Organisation name">
                <TextInput
                  value={form.name}
                  onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
                  placeholder="Example Travel Company"
                  required
                />
              </FormField>
              <FormField label="Organisation key" help="A short lowercase label used for imports, such as example-travel-company.">
                <TextInput
                  value={form.slug}
                  onChange={(event) => setForm((current) => ({ ...current, slug: event.target.value }))}
                  placeholder="example-travel-company"
                />
              </FormField>
              <FormField label="Contact email">
                <TextInput
                  type="email"
                  value={form.contact_email}
                  onChange={(event) => setForm((current) => ({ ...current, contact_email: event.target.value }))}
                  placeholder="owner@example.com"
                />
              </FormField>
              <FormField label="Internal notes">
                <TextArea
                  value={form.notes}
                  onChange={(event) => setForm((current) => ({ ...current, notes: event.target.value }))}
                  placeholder="Optional notes for this organisation"
                />
              </FormField>
              <div className="lg:col-span-2">
                <PrimaryButton type="submit" icon={Plus} disabled={saving}>
                  {saving ? "Creating..." : "Create organisation"}
                </PrimaryButton>
              </div>
            </form>
          </Card>
        ) : null}

        <Card title="Organisations" description={isSuperAdmin ? "Super Admin can see every company on the portal." : "Your admin access is limited to this organisation."}>
          <DataTable
            rows={organizations.data || []}
            emptyMessage="No organisations have been created yet."
            columns={[
              { key: "name", label: "Name" },
              { key: "slug", label: "Key" },
              { key: "status", label: "Status", render: (row) => <StatusBadge status={row.status} /> },
              { key: "contact_email", label: "Contact email" },
            ]}
          />
        </Card>
      </div>
    </AdminPageShell>
  );
}

function Rule({ label, value }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <dt className="font-medium text-slate-700">{label}</dt>
      <dd className="text-right text-slate-600">{value}</dd>
    </div>
  );
}
