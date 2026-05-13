import { Save } from "lucide-react";
import { useEffect, useState } from "react";

import {
  Card,
  ErrorBanner,
  FormField,
  LoadingState,
  PageHeader,
  PrimaryButton,
  StatusBadge,
  TextArea,
  TextInput,
} from "../../components/ui.jsx";
import { useAuth } from "../../context/AuthContext.jsx";
import { getFriendlyError, saveAgentProfile, useAgentProfile } from "../../hooks/useAgentPortalData.js";
import { formatDateTime } from "../../utils/formatters.js";

const blankProfile = {
  first_name: "",
  last_name: "",
  email: "",
  personal_email: "",
  company_email: "",
  phone: "",
  business_name: "",
  joining_date: "",
  address: "",
  postcode: "",
  commission_bank_name: "",
  commission_account_name: "",
  commission_sort_code: "",
  commission_account_number: "",
};

export default function ProfilePage() {
  const { token, user } = useAuth();
  const { profile, setProfile, loading, error, refreshProfile } = useAgentProfile();
  const [values, setValues] = useState(blankProfile);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState("");
  const [saveMessage, setSaveMessage] = useState("");

  useEffect(() => {
    if (profile) {
      setValues({
        first_name: profile.first_name || "",
        last_name: profile.last_name || "",
        email: profile.email || "",
        personal_email: profile.personal_email || "",
        company_email: profile.company_email || "",
        phone: profile.phone || "",
        business_name: profile.business_name || "",
        joining_date: profile.joining_date || "",
        address: profile.address || "",
        postcode: profile.postcode || "",
        commission_bank_name: profile.commission_bank_name || "",
        commission_account_name: profile.commission_account_name || "",
        commission_sort_code: profile.commission_sort_code || "",
        commission_account_number: profile.commission_account_number || "",
      });
    } else if (user?.email) {
      setValues((current) => ({ ...current, email: user.email }));
    }
  }, [profile, user]);

  function updateValue(field, value) {
    setValues((current) => ({ ...current, [field]: value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setSaving(true);
    setSaveError("");
    setSaveMessage("");

    try {
      const savedProfile = await saveAgentProfile({ token, profile, values });
      setProfile(savedProfile);
      await refreshProfile();
      setSaveMessage("Profile saved.");
    } catch (err) {
      setSaveError(getFriendlyError(err, "We could not save the profile."));
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <PageHeader title="My Profile" description="Your profile stores the key contact, business, and commission details for onboarding." />
        <LoadingState message="Loading your profile..." />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Agent portal"
        title="My Profile"
        description="Keep your personal, business, and commission payment details up to date."
      />

      <ErrorBanner message={error || saveError} />

      {saveMessage ? (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm font-medium text-emerald-700">
          {saveMessage}
        </div>
      ) : null}

      {profile ? (
        <Card title="Profile Status">
          <dl className="grid gap-4 text-sm md:grid-cols-4">
            <div>
              <dt className="text-slate-500">Current status</dt>
              <dd className="mt-1">
                <StatusBadge status={profile.status} />
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">Agent ID</dt>
              <dd className="mt-1 font-medium text-slate-900">{profile.agent_id || "Not assigned yet"}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Created</dt>
              <dd className="mt-1 font-medium text-slate-900">{formatDateTime(profile.created_at)}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Last updated</dt>
              <dd className="mt-1 font-medium text-slate-900">{formatDateTime(profile.updated_at)}</dd>
            </div>
          </dl>
        </Card>
      ) : null}

      <form onSubmit={handleSubmit} className="space-y-6">
        <Card title={profile ? "Edit Profile" : "Create Profile"} description="These details help the admin team finish your onboarding checks.">
          <div className="grid gap-4 md:grid-cols-2">
            <FormField label="First name">
              <TextInput required value={values.first_name} onChange={(event) => updateValue("first_name", event.target.value)} />
            </FormField>
            <FormField label="Last name">
              <TextInput required value={values.last_name} onChange={(event) => updateValue("last_name", event.target.value)} />
            </FormField>
            <FormField label="Email address">
              <TextInput required type="email" value={values.email} onChange={(event) => updateValue("email", event.target.value)} />
            </FormField>
            <FormField label="Personal email">
              <TextInput type="email" value={values.personal_email} onChange={(event) => updateValue("personal_email", event.target.value)} />
            </FormField>
            <FormField label="One Travel Club email">
              <TextInput type="email" value={values.company_email} onChange={(event) => updateValue("company_email", event.target.value)} />
            </FormField>
            <FormField label="Phone number">
              <TextInput value={values.phone} onChange={(event) => updateValue("phone", event.target.value)} />
            </FormField>
            <FormField label="Business name">
              <TextInput value={values.business_name} onChange={(event) => updateValue("business_name", event.target.value)} />
            </FormField>
            <FormField label="Joining date">
              <TextInput type="date" value={values.joining_date || ""} onChange={(event) => updateValue("joining_date", event.target.value)} />
            </FormField>
            <FormField label="Address">
              <TextArea value={values.address} onChange={(event) => updateValue("address", event.target.value)} />
            </FormField>
            <FormField label="Postcode">
              <TextInput value={values.postcode} onChange={(event) => updateValue("postcode", event.target.value)} />
            </FormField>
          </div>
        </Card>

        <Card title="Commission Bank Details" description="These details are for recording where commission should be paid.">
          <div className="grid gap-4 md:grid-cols-2">
            <FormField label="Bank name">
              <TextInput value={values.commission_bank_name} onChange={(event) => updateValue("commission_bank_name", event.target.value)} />
            </FormField>
            <FormField label="Account name">
              <TextInput value={values.commission_account_name} onChange={(event) => updateValue("commission_account_name", event.target.value)} />
            </FormField>
            <FormField label="Sort code">
              <TextInput value={values.commission_sort_code} onChange={(event) => updateValue("commission_sort_code", event.target.value)} />
            </FormField>
            <FormField label="Account number">
              <TextInput
                value={values.commission_account_number}
                onChange={(event) => updateValue("commission_account_number", event.target.value)}
              />
            </FormField>
          </div>
        </Card>

        <div className="flex justify-end">
          <PrimaryButton type="submit" icon={Save} disabled={saving}>
            {saving ? "Saving..." : "Save profile"}
          </PrimaryButton>
        </div>
      </form>
    </div>
  );
}
