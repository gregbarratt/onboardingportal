import { CalendarCheck, CheckCircle2, ExternalLink, Video } from "lucide-react";

import { Card, DataTable, EmptyState, ErrorBanner, LoadingState, StatCard, StatusBadge } from "../../components/ui.jsx";
import { useAgentResource, useApiResource } from "../../hooks/useAgentPortalData.js";
import AgentPageShell from "./AgentPageShell.jsx";

export default function LiveCallsPage() {
  return (
    <AgentPageShell
      title="Live Training and Call Check List"
      description="See the live training calls you need to attend and your attendance status."
    >
      {({ profile }) => <LiveCallsContent profile={profile} />}
    </AgentPageShell>
  );
}

function LiveCallsContent({ profile }) {
  const sessions = useApiResource("/live-sessions", { initialData: [] });
  const attendance = useAgentResource(profile, (id) => `/agents/${id}/attendance`, {
    initialData: [],
  });

  if (sessions.loading || attendance.loading) {
    return <LoadingState message="Loading live calls..." />;
  }

  const sessionRows = sessions.data || [];
  const attendanceRows = attendance.data || [];
  const attendanceBySessionId = new Map(attendanceRows.map((item) => [item.session_id, item]));
  const attendedCount = attendanceRows.filter((item) => ["Attended", "Watched Recording"].includes(item.attendance_status)).length;
  const allocatedCount = attendanceRows.length;

  return (
    <div className="space-y-6">
      <ErrorBanner message={sessions.error || attendance.error} />

      <div className="grid gap-4 md:grid-cols-3">
        <StatCard label="Live calls" value={sessionRows.length} icon={Video} />
        <StatCard label="Allocated to me" value={allocatedCount} icon={CalendarCheck} />
        <StatCard label="Attended" value={`${attendedCount}/${allocatedCount || 0}`} icon={CheckCircle2} />
      </div>

      <Card title="Live Training and Call Check List" description="Admin can update these calls, hosts, links, and attendance from the admin area.">
        {sessionRows.length ? (
          <div className="grid gap-4 lg:grid-cols-2">
            {sessionRows.map((session) => {
              const attendanceRecord = attendanceBySessionId.get(session.id);
              const attendanceStatus = attendanceRecord?.attendance_status || "Not allocated";
              const complete = ["Attended", "Watched Recording"].includes(attendanceStatus);

              return (
                <article key={session.id} className="rounded-lg border border-slate-200 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <h2 className="text-sm font-semibold text-slate-950">{session.title}</h2>
                      <p className="mt-1 text-xs font-medium text-slate-500">{session.session_type}</p>
                    </div>
                    <div className="flex flex-col items-end gap-2">
                      <StatusBadge status={session.attendance_required ? "Required" : "Optional"} />
                      <span className="inline-flex items-center gap-1.5">
                        {complete ? <CheckCircle2 className="h-4 w-4 text-emerald-700" aria-hidden="true" /> : null}
                        <StatusBadge status={attendanceStatus} />
                      </span>
                    </div>
                  </div>
                  <p className="mt-3 text-sm text-slate-600">{session.description || "No description added yet."}</p>
                  <div className="mt-4 grid gap-2 text-sm text-slate-600 sm:grid-cols-2">
                    <span>Host: {session.trainer_host || "Nikki Bishop"}</span>
                    <span>Time: {session.start_time || "Not set"} to {session.end_time || "Not set"}</span>
                  </div>
                  <div className="mt-4 flex flex-wrap gap-2">
                    <SessionLink label="Join meeting" url={session.meeting_link} />
                    <SessionLink label="Watch recording" url={session.recording_link} />
                  </div>
                </article>
              );
            })}
          </div>
        ) : (
          <EmptyState title="No live sessions yet" message="Welcome calls, compliance calls, and training sessions will appear here." />
        )}
      </Card>

      <Card title="My Attendance">
        <DataTable
          rows={attendanceRows}
          emptyMessage="No attendance has been logged yet."
          columns={[
            { key: "session", label: "Session", render: (row) => row.session?.title || "Session" },
            { key: "session_type", label: "Type", render: (row) => row.session?.session_type || "Not set" },
            { key: "attendance_status", label: "Status", render: (row) => <StatusBadge status={row.attendance_status} /> },
            { key: "watched_recording", label: "Recording", render: (row) => (row.watched_recording ? "Watched" : "Not marked") },
          ]}
        />
      </Card>
    </div>
  );
}

function SessionLink({ label, url }) {
  if (!url) return null;

  return (
    <a href={url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50">
      {label}
      <ExternalLink className="h-4 w-4" aria-hidden="true" />
    </a>
  );
}
