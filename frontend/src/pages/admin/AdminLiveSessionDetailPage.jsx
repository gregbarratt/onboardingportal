import { Save, UserPlus } from "lucide-react";
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { Card, DataTable, ErrorBanner, FormField, LoadingState, PrimaryButton, SelectInput, StatusBadge, TextArea, TextInput } from "../../components/ui.jsx";
import { apiClient } from "../../api/client.js";
import { useAuth } from "../../context/AuthContext.jsx";
import { buildAgentName, useAgents } from "../../hooks/useAdminData.js";
import { getFriendlyError, useApiResource } from "../../hooks/useAgentPortalData.js";
import { formatDate } from "../../utils/formatters.js";
import { attendanceStatuses, liveSessionTypes } from "./adminConstants.js";
import AdminPageShell, { AdminLinkButton } from "./AdminPageShell.jsx";

export default function AdminLiveSessionDetailPage() {
  const { sessionId } = useParams();
  const { token } = useAuth();
  const session = useApiResource(`/live-sessions/${sessionId}`, {
    fallbackError: "We could not load this live session.",
  });
  const agents = useAgents();
  const [form, setForm] = useState({});
  const [attendanceForm, setAttendanceForm] = useState({
    agent_id: "",
    attendance_status: "Attended",
    marked_date: "",
    duration_attended: "",
    notes: "",
    watched_recording: false,
  });
  const [saving, setSaving] = useState(false);
  const [marking, setMarking] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (session.data) {
      setForm({
        title: session.data.title || "",
        session_type: session.data.session_type || "Welcome Call",
        description: session.data.description || "",
        date: session.data.date || "",
        start_time: session.data.start_time || "",
        end_time: session.data.end_time || "",
        trainer_host: session.data.trainer_host || "",
        meeting_link: session.data.meeting_link || "",
        recording_link: session.data.recording_link || "",
        attendance_required: Boolean(session.data.attendance_required),
        follow_up_quiz_required: Boolean(session.data.follow_up_quiz_required),
        certificate_issued: Boolean(session.data.certificate_issued),
        notes: session.data.notes || "",
      });
    }
  }, [session.data]);

  function update(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function updateAttendance(field, value) {
    setAttendanceForm((current) => ({ ...current, [field]: value }));
  }

  async function saveSession(event) {
    event.preventDefault();
    setSaving(true);
    setError("");
    setMessage("");

    try {
      await apiClient.put(
        `/live-sessions/${sessionId}`,
        {
          ...form,
          start_time: form.start_time || null,
          end_time: form.end_time || null,
        },
        token,
      );
      await session.reload();
      setMessage("Live session saved.");
    } catch (err) {
      setError(getFriendlyError(err, "We could not save this live session."));
    } finally {
      setSaving(false);
    }
  }

  async function markAttendance(event) {
    event.preventDefault();
    setMarking(true);
    setError("");
    setMessage("");

    try {
      await apiClient.post(
        `/live-sessions/${sessionId}/attendance`,
        {
          ...attendanceForm,
          agent_id: Number(attendanceForm.agent_id),
          marked_date: attendanceForm.marked_date || null,
          duration_attended: attendanceForm.duration_attended === "" ? null : Number(attendanceForm.duration_attended),
        },
        token,
      );
      setAttendanceForm({ agent_id: "", attendance_status: "Attended", marked_date: "", duration_attended: "", notes: "", watched_recording: false });
      setMessage("Attendance marked.");
    } catch (err) {
      setError(getFriendlyError(err, "We could not mark attendance."));
    } finally {
      setMarking(false);
    }
  }

  if (session.loading || agents.loading) {
    return (
      <AdminPageShell title="Live Training Session Detail" description="Loading live session.">
        <LoadingState message="Loading session detail..." />
      </AdminPageShell>
    );
  }

  return (
    <AdminPageShell
      title="Live Training Session Detail"
      description="Edit a live call and mark attendance for agents."
      actions={<AdminLinkButton to="/admin/live-sessions">All live sessions</AdminLinkButton>}
    >
      <div className="space-y-6">
        <ErrorBanner message={session.error || agents.error || error} />
        {message ? <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm font-medium text-emerald-700">{message}</div> : null}

        <form onSubmit={saveSession}>
          <Card title="Session Details">
            <div className="grid gap-4 md:grid-cols-3">
              <FormField label="Title">
                <TextInput value={form.title || ""} onChange={(event) => update("title", event.target.value)} />
              </FormField>
              <FormField label="Session type">
                <SelectInput value={form.session_type || "Welcome Call"} onChange={(event) => update("session_type", event.target.value)}>
                  {liveSessionTypes.map((type) => <option key={type} value={type}>{type}</option>)}
                </SelectInput>
              </FormField>
              <FormField label="Date">
                <TextInput type="date" value={form.date || ""} onChange={(event) => update("date", event.target.value)} />
              </FormField>
              <FormField label="Start time">
                <TextInput type="time" value={form.start_time || ""} onChange={(event) => update("start_time", event.target.value)} />
              </FormField>
              <FormField label="End time">
                <TextInput type="time" value={form.end_time || ""} onChange={(event) => update("end_time", event.target.value)} />
              </FormField>
              <FormField label="Host">
                <TextInput value={form.trainer_host || ""} onChange={(event) => update("trainer_host", event.target.value)} />
              </FormField>
              <FormField label="Meeting link">
                <TextInput value={form.meeting_link || ""} onChange={(event) => update("meeting_link", event.target.value)} />
              </FormField>
              <FormField label="Recording link">
                <TextInput value={form.recording_link || ""} onChange={(event) => update("recording_link", event.target.value)} />
              </FormField>
              <div className="flex items-end gap-4">
                <Checkbox label="Attendance required" checked={Boolean(form.attendance_required)} onChange={(value) => update("attendance_required", value)} />
              </div>
              <div className="md:col-span-3">
                <FormField label="Description">
                  <TextArea value={form.description || ""} onChange={(event) => update("description", event.target.value)} />
                </FormField>
              </div>
            </div>
            <div className="mt-4">
              <PrimaryButton type="submit" icon={Save} disabled={saving}>{saving ? "Saving..." : "Save session"}</PrimaryButton>
            </div>
          </Card>
        </form>

        <form onSubmit={markAttendance}>
          <Card title="Mark Attendance">
            <div className="grid gap-4 md:grid-cols-3">
              <FormField label="Agent">
                <SelectInput required value={attendanceForm.agent_id} onChange={(event) => updateAttendance("agent_id", event.target.value)}>
                  <option value="">Choose agent</option>
                  {(agents.data || []).map((agent) => <option key={agent.id} value={agent.id}>{buildAgentName(agent)}</option>)}
                </SelectInput>
              </FormField>
              <FormField label="Attendance status">
                <SelectInput value={attendanceForm.attendance_status} onChange={(event) => updateAttendance("attendance_status", event.target.value)}>
                  {attendanceStatuses.map((status) => <option key={status} value={status}>{status}</option>)}
                </SelectInput>
              </FormField>
              <FormField label="Marked date">
                <TextInput type="date" value={attendanceForm.marked_date} onChange={(event) => updateAttendance("marked_date", event.target.value)} />
              </FormField>
              <FormField label="Duration attended">
                <TextInput type="number" min="0" value={attendanceForm.duration_attended} onChange={(event) => updateAttendance("duration_attended", event.target.value)} />
              </FormField>
              <div className="flex items-end">
                <Checkbox label="Watched recording" checked={attendanceForm.watched_recording} onChange={(value) => updateAttendance("watched_recording", value)} />
              </div>
              <div className="md:col-span-3">
                <FormField label="Notes">
                  <TextArea value={attendanceForm.notes} onChange={(event) => updateAttendance("notes", event.target.value)} />
                </FormField>
              </div>
            </div>
            <div className="mt-4">
              <PrimaryButton type="submit" icon={UserPlus} disabled={marking}>{marking ? "Marking..." : "Mark attendance"}</PrimaryButton>
            </div>
          </Card>
        </form>

        <Card title="Session Summary">
          <DataTable
            rows={session.data ? [session.data] : []}
            columns={[
              { key: "title", label: "Title" },
              { key: "session_type", label: "Type" },
              { key: "date", label: "Date", render: (row) => formatDate(row.date) },
              { key: "attendance_required", label: "Attendance", render: (row) => <StatusBadge status={row.attendance_required ? "Required" : "Optional"} /> },
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
