import { Building2, Mail, Plus, Send, UsersRound } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { apiClient } from "../../api/client.js";
import {
  Card,
  DataTable,
  ErrorBanner,
  FormField,
  LoadingState,
  PrimaryButton,
  SelectInput,
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

const teamManagerRoles = ["Super Admin", "Organisation Admin", "Admin"];
const standardRoleOptions = [
  { value: "Agent", label: "Agent" },
  { value: "Training Manager", label: "Trainer" },
  { value: "Admin", label: "Admin" },
];
const superAdminRoleOptions = [
  ...standardRoleOptions,
  { value: "Super Admin", label: "Super Admin" },
];

function roleLabel(roleName) {
  if (roleName === "Training Manager") return "Trainer";
  if (roleName === "Organisation Admin") return "Admin";
  return roleName || "Not set";
}

export default function AdminSettingsPage() {
  const { token, user } = useAuth();
  const isSuperAdmin = user?.role?.name === "Super Admin";
  const canManageUserLevels = teamManagerRoles.includes(user?.role?.name);
  const organizations = useApiResource("/organizations", {
    fallbackError: "We could not load organisations.",
    initialData: [],
  });
  const teamUsers = useApiResource("/auth/users", {
    enabled: canManageUserLevels,
    fallbackError: "We could not load team users.",
    initialData: [],
  });
  const [form, setForm] = useState(emptyOrganizationForm);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState("");
  const [userLevelError, setUserLevelError] = useState("");
  const [updatingUserId, setUpdatingUserId] = useState(null);
  const [emailTestAddress, setEmailTestAddress] = useState(user?.email || "");
  const [testingEmail, setTestingEmail] = useState(false);
  const [emailTestMessage, setEmailTestMessage] = useState("");
  const [emailTestError, setEmailTestError] = useState("");

  const currentOrganization = useMemo(() => {
    if (user?.organization) return user.organization;
    return organizations.data?.find((item) => item.id === user?.organization_id) || null;
  }, [organizations.data, user]);

  useEffect(() => {
    if (user?.email && !emailTestAddress) {
      setEmailTestAddress(user.email);
    }
  }, [emailTestAddress, user]);

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

  async function handleSendEmailTest(event) {
    event.preventDefault();
    setTestingEmail(true);
    setEmailTestMessage("");
    setEmailTestError("");

    try {
      const response = await apiClient.post("/admin/email-test", { to_email: emailTestAddress }, token);
      setEmailTestMessage(response.message || "Test email sent.");
    } catch (err) {
      setEmailTestError(getFriendlyError(err, "Email test failed."));
    } finally {
      setTestingEmail(false);
    }
  }

  async function handleRoleChange(targetUser, nextRoleName) {
    if (!nextRoleName || nextRoleName === targetUser.role?.name) return;

    setUpdatingUserId(targetUser.id);
    setUserLevelError("");

    try {
      await apiClient.put(`/auth/users/${targetUser.id}/role`, { role_name: nextRoleName }, token);
      await teamUsers.reload();
    } catch (err) {
      setUserLevelError(getFriendlyError(err, "User level could not be updated."));
    } finally {
      setUpdatingUserId(null);
    }
  }

  function roleOptionsFor(targetUser) {
    const baseOptions = isSuperAdmin ? superAdminRoleOptions : standardRoleOptions;
    if (!targetUser.role?.name || baseOptions.some((option) => option.value === targetUser.role.name)) {
      return baseOptions;
    }
    return [...baseOptions, { value: targetUser.role.name, label: roleLabel(targetUser.role.name) }];
  }

  if (organizations.loading || (canManageUserLevels && teamUsers.loading)) {
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
        <ErrorBanner message={teamUsers.error} />
        <ErrorBanner message={userLevelError} />
        <ErrorBanner message={emailTestError} />
        {emailTestMessage ? <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm font-medium text-emerald-700">{emailTestMessage}</div> : null}

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
              <Rule label="Agent" value="Can only use their own agent portal." />
              <Rule label="Trainer" value="Can manage training and onboarding, but cannot see payment admin." />
              <Rule label="Admin" value="Can manage the full organisation, including payments." />
              <Rule label="Super Admin" value="Can manage every organisation and every user." />
            </dl>
          </Card>
        </div>

        {canManageUserLevels ? (
          <Card
            title="Team User Levels"
            description={isSuperAdmin ? "Change an existing portal user to Agent, Trainer, Admin, or Super Admin." : "Change an existing portal user to Agent, Trainer, or Admin."}
            actions={
              <span className="rounded-lg bg-sky-50 p-2 text-sky-700">
                <UsersRound className="h-5 w-5" aria-hidden="true" />
              </span>
            }
          >
            <DataTable
              rows={teamUsers.data || []}
              emptyMessage="No users have been created yet."
              columns={[
                {
                  key: "user",
                  label: "User",
                  render: (row) => (
                    <div>
                      <p className="font-semibold text-slate-950">
                        {row.agent_profile ? `${row.agent_profile.first_name} ${row.agent_profile.last_name}` : row.email}
                      </p>
                      <p className="text-xs text-slate-500">{row.email}</p>
                    </div>
                  ),
                },
                {
                  key: "role",
                  label: "User level",
                  render: (row) =>
                    row.id === user?.id ? (
                      <div className="space-y-1">
                        <StatusBadge status={roleLabel(row.role?.name)} />
                        <p className="text-xs text-slate-500">Your own level</p>
                      </div>
                    ) : (
                      <SelectInput
                        value={row.role?.name || ""}
                        disabled={updatingUserId === row.id}
                        onChange={(event) => handleRoleChange(row, event.target.value)}
                      >
                        {roleOptionsFor(row).map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </SelectInput>
                    ),
                },
                {
                  key: "organization",
                  label: "Organisation",
                  render: (row) => row.organization?.name || "Not set",
                },
                {
                  key: "status",
                  label: "Status",
                  render: (row) => <StatusBadge status={row.is_active ? "Active" : "Inactive"} />,
                },
              ]}
            />
          </Card>
        ) : null}

        <Card title="Email Test" description="Send a test email from the same mailbox used for password resets.">
          <form onSubmit={handleSendEmailTest} className="grid gap-4 lg:grid-cols-[1fr_auto] lg:items-end">
            <FormField label="Send test email to">
              <TextInput
                type="email"
                value={emailTestAddress}
                onChange={(event) => setEmailTestAddress(event.target.value)}
                placeholder="name@example.com"
                required
              />
            </FormField>
            <PrimaryButton type="submit" icon={testingEmail ? Mail : Send} disabled={testingEmail}>
              {testingEmail ? "Sending..." : "Send test email"}
            </PrimaryButton>
          </form>
        </Card>

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
