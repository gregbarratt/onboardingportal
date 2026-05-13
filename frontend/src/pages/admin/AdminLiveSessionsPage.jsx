import { Plus } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { Card, DataTable, ErrorBanner, FormField, LoadingState, PrimaryButton, SelectInput, StatusBadge, TextArea, TextInput } from "../../components/ui.jsx";
import { apiClient } from "../../api/client.js";
import { useAuth } from "../../context/AuthContext.jsx";
import { getFriendlyError, useApiResource } from "../../hooks/useAgentPortalData.js";
import { formatDate } from "../../utils/formatters.js";
import { liveSessionTypes } from "./adminConstants.js";
import AdminPageShell from "./AdminPageShell.jsx";

const blankSession = {
  title: "",
  session_type: "Welcome Call",
  description: "",
  date: "",
  start_time: "",
  end_time: "",
  trainer_host: "",
  meeting_link: "",
  recording_link: "",
  attendance_required: true,
  follow_up_quiz_required: false,
  certificate_issued: false,
  notes: "",
};

export default function AdminLiveSessionsPage() {
  const { token } = useAuth();
  const sessions = useApiResource("/live-sessions", {
    initialData: [],
    fallbackError: "We could not load live sessions.",
  });
  const [form, setForm] = useState(blankSession);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  function update(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function createSession(event) {
    event.preventDefault();
    setSaving(true);
    setMessage("");
    setError("");

    try {
      await apiClient.post(
        "/live-sessions",
        {
          ...form,
          start_time: form.start_time || null,
          end_time: form.end_time || null,
        },
        token,
      );
      setForm(blankSession);
      await sessions.reload();
      setMessage("Live session created.");
    } catch (err) {
      setError(getFriendlyError(err, "We could not create this live session."));
    } finally {
      setSaving(false);
    }
  }

  if (sessions.loading) {
    return (
      <AdminPageShell title="Live Training Session List" description="Loading live sessions.">
        <LoadingState message="Loading live sessions..." />
      </AdminPageShell>
    );
  }

  return (
    <AdminPageShell title="Live Training Session List" description="Create live calls and open sessions to manage attendance.">
      <div className="space-y-6">
        <ErrorBanner message={sessions.error || error} />
        {message ? <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm font-medium text-emerald-700">{message}</div> : null}

        <Card title="Create Live Session">
          <form onSubmit={createSession} className="grid gap-4 md:grid-cols-3">
            <FormField label="Title">
              <TextInput required value={form.title} onChange={(event) => update("title", event.target.value)} />
            </FormField>
            <FormField label="Session type">
              <SelectInput value={form.session_type} onChange={(event) => update("session_type", event.target.value)}>
                {liveSessionTypes.map((type) => <option key={type} value={type}>{type}</option>)}
              </SelectInput>
            </FormField>
            <FormField label="Date">
              <TextInput required type="date" value={form.date} onChange={(event) => update("date", event.target.value)} />
            </FormField>
            <FormField label="Start time">
              <TextInput type="time" value={form.start_time} onChange={(event) => update("start_time", event.target.value)} />
            </FormField>
            <FormField label="End time">
              <TextInput type="time" value={form.end_time} onChange={(event) => update("end_time", event.target.value)} />
            </FormField>
            <FormField label="Trainer or host">
              <TextInput value={form.trainer_host} onChange={(event) => update("trainer_host", event.target.value)} />
            </FormField>
            <FormField label="Meeting link">
              <TextInput value={form.meeting_link} onChange={(event) => update("meeting_link", event.target.value)} />
            </FormField>
            <FormField label="Recording link">
              <TextInput value={form.recording_link} onChange={(event) => update("recording_link", event.target.value)} />
            </FormField>
            <div className="flex items-end gap-4">
              <Checkbox label="Attendance required" checked={form.attendance_required} onChange={(value) => update("attendance_required", value)} />
            </div>
            <div className="md:col-span-3">
              <FormField label="Description">
                <TextArea value={form.description} onChange={(event) => update("description", event.target.value)} />
              </FormField>
            </div>
            <div className="md:col-span-3">
              <PrimaryButton type="submit" icon={Plus} disabled={saving}>{saving ? "Creating..." : "Create session"}</PrimaryButton>
            </div>
          </form>
        </Card>

        <Card title="Live Sessions">
          <DataTable
            rows={sessions.data || []}
            emptyMessage="No live sessions have been created yet."
            columns={[
              { key: "title", label: "Session", render: (row) => <Link className="font-semibold text-sky-700 hover:text-sky-900" to={`/admin/live-sessions/${row.id}`}>{row.title}</Link> },
              { key: "session_type", label: "Type" },
              { key: "date", label: "Date", render: (row) => formatDate(row.date) },
              { key: "trainer_host", label: "Host" },
              { key: "attendance_required", label: "Required", render: (row) => <StatusBadge status={row.attendance_required ? "Required" : "Optional"} /> },
              { key: "open", label: "Open", render: (row) => <Link className="font-semibold text-sky-700 hover:text-sky-900" to={`/admin/live-sessions/${row.id}`}>Manage</Link> },
            ]}
          />
        </Card>
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
