import { Save } from "lucide-react";
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import {
  Card,
  ErrorBanner,
  FormField,
  LoadingState,
  PrimaryButton,
  SelectInput,
  TextArea,
  TextInput,
} from "../../components/ui.jsx";
import { apiClient } from "../../api/client.js";
import { useAuth } from "../../context/AuthContext.jsx";
import { getFriendlyError, useApiResource } from "../../hooks/useAgentPortalData.js";
import { trainingPublishedStatuses, trainingTracks } from "./adminConstants.js";
import AdminPageShell, { AdminLinkButton } from "./AdminPageShell.jsx";

const blankModule = {
  title: "",
  description: "",
  category_id: "1",
  level: "Beginner",
  mandatory: false,
  estimated_completion_time: "30 minutes",
  content_type: "Text",
  content_url: "",
  video_url: "",
  pdf_url: "",
  text_content: "",
  quiz_required: false,
  pass_mark: "",
  certificate_issued: false,
  renewal_required: false,
  renewal_period_months: "",
  expiry_date: "",
  training_track: "Onboarding",
  published_status: "Draft",
};

export default function AdminTrainingModuleBuilderPage() {
  const { moduleId } = useParams();
  const { token } = useAuth();
  const existingModule = useApiResource(moduleId ? `/training/modules/${moduleId}` : "", {
    enabled: Boolean(moduleId),
    fallbackError: "We could not load this training module.",
  });
  const [form, setForm] = useState(blankModule);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (existingModule.data) {
      setForm({
        title: existingModule.data.title || "",
        description: existingModule.data.description || "",
        category_id: String(existingModule.data.category_id || "1"),
        level: existingModule.data.level || "Beginner",
        mandatory: Boolean(existingModule.data.mandatory),
        estimated_completion_time: existingModule.data.estimated_completion_time || "30 minutes",
        content_type: existingModule.data.content_type || "Text",
        content_url: existingModule.data.content_url || "",
        video_url: existingModule.data.video_url || "",
        pdf_url: existingModule.data.pdf_url || "",
        text_content: existingModule.data.text_content || "",
        quiz_required: Boolean(existingModule.data.quiz_required),
        pass_mark: existingModule.data.pass_mark ?? "",
        certificate_issued: Boolean(existingModule.data.certificate_issued),
        renewal_required: Boolean(existingModule.data.renewal_required),
        renewal_period_months: existingModule.data.renewal_period_months ?? "",
        expiry_date: existingModule.data.expiry_date || "",
        training_track: existingModule.data.training_track || "Onboarding",
        published_status: existingModule.data.published_status || "Draft",
      });
    }
  }, [existingModule.data]);

  function update(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function saveModule(event) {
    event.preventDefault();
    setSaving(true);
    setMessage("");
    setError("");

    const payload = {
      ...form,
      category_id: Number(form.category_id),
      pass_mark: form.pass_mark === "" ? null : Number(form.pass_mark),
      renewal_period_months: form.renewal_period_months === "" ? null : Number(form.renewal_period_months),
      expiry_date: form.expiry_date || null,
    };

    try {
      if (moduleId) {
        await apiClient.put(`/training/modules/${moduleId}`, payload, token);
      } else {
        await apiClient.post("/training/modules", payload, token);
        setForm(blankModule);
      }
      setMessage("Training module saved.");
    } catch (err) {
      setError(getFriendlyError(err, "We could not save this training module."));
    } finally {
      setSaving(false);
    }
  }

  if (existingModule.loading) {
    return (
      <AdminPageShell title="Training Module Builder" description="Loading training module.">
        <LoadingState message="Loading module builder..." />
      </AdminPageShell>
    );
  }

  return (
    <AdminPageShell
      title="Training Module Builder"
      description="Create or edit training lessons, resources, quizzes, certificates, and renewal settings."
      actions={<AdminLinkButton to="/admin/training">Back to modules</AdminLinkButton>}
    >
      <div className="space-y-6">
        <ErrorBanner message={existingModule.error || error} />
        {message ? <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm font-medium text-emerald-700">{message}</div> : null}

        <form onSubmit={saveModule}>
          <Card title={moduleId ? "Edit Module" : "New Module"}>
            <div className="grid gap-4 md:grid-cols-2">
              <FormField label="Title">
                <TextInput required value={form.title} onChange={(event) => update("title", event.target.value)} />
              </FormField>
              <FormField label="Category ID" help="Temporary field until a category picker is added. Default categories are seeded by the backend.">
                <TextInput required type="number" min="1" value={form.category_id} onChange={(event) => update("category_id", event.target.value)} />
              </FormField>
              <FormField label="Level">
                <TextInput value={form.level} onChange={(event) => update("level", event.target.value)} />
              </FormField>
              <FormField label="Estimated completion time">
                <TextInput value={form.estimated_completion_time} onChange={(event) => update("estimated_completion_time", event.target.value)} />
              </FormField>
              <FormField label="Training track">
                <SelectInput value={form.training_track} onChange={(event) => update("training_track", event.target.value)}>
                  {trainingTracks.map((track) => <option key={track} value={track}>{track}</option>)}
                </SelectInput>
              </FormField>
              <FormField label="Published status">
                <SelectInput value={form.published_status} onChange={(event) => update("published_status", event.target.value)}>
                  {trainingPublishedStatuses.map((status) => <option key={status} value={status}>{status}</option>)}
                </SelectInput>
              </FormField>
              <FormField label="Content type">
                <TextInput value={form.content_type} onChange={(event) => update("content_type", event.target.value)} />
              </FormField>
              <FormField label="Pass mark">
                <TextInput type="number" min="0" max="100" value={form.pass_mark} onChange={(event) => update("pass_mark", event.target.value)} />
              </FormField>
              <FormField label="Content URL">
                <TextInput value={form.content_url} onChange={(event) => update("content_url", event.target.value)} />
              </FormField>
              <FormField label="Video URL">
                <TextInput value={form.video_url} onChange={(event) => update("video_url", event.target.value)} />
              </FormField>
              <FormField label="PDF URL">
                <TextInput value={form.pdf_url} onChange={(event) => update("pdf_url", event.target.value)} />
              </FormField>
              <FormField label="Expiry date">
                <TextInput type="date" value={form.expiry_date} onChange={(event) => update("expiry_date", event.target.value)} />
              </FormField>
              <div className="md:col-span-2">
                <FormField label="Description">
                  <TextArea value={form.description} onChange={(event) => update("description", event.target.value)} />
                </FormField>
              </div>
              <div className="md:col-span-2">
                <FormField label="Written lesson content">
                  <TextArea value={form.text_content} onChange={(event) => update("text_content", event.target.value)} />
                </FormField>
              </div>
              <div className="md:col-span-2 flex flex-wrap gap-5">
                <Checkbox label="Mandatory" checked={form.mandatory} onChange={(value) => update("mandatory", value)} />
                <Checkbox label="Quiz required" checked={form.quiz_required} onChange={(value) => update("quiz_required", value)} />
                <Checkbox label="Certificate issued" checked={form.certificate_issued} onChange={(value) => update("certificate_issued", value)} />
                <Checkbox label="Renewal required" checked={form.renewal_required} onChange={(value) => update("renewal_required", value)} />
              </div>
              <FormField label="Renewal period months">
                <TextInput type="number" min="1" value={form.renewal_period_months} onChange={(event) => update("renewal_period_months", event.target.value)} />
              </FormField>
            </div>
            <div className="mt-4">
              <PrimaryButton type="submit" icon={Save} disabled={saving}>
                {saving ? "Saving..." : "Save module"}
              </PrimaryButton>
            </div>
          </Card>
        </form>
      </div>
    </AdminPageShell>
  );
}

function Checkbox({ label, checked, onChange }) {
  return (
    <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
      <input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} />
      {label}
    </label>
  );
}
