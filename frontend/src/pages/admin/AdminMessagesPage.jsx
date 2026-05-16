import { MessageSquare, RefreshCw, Send } from "lucide-react";
import { useEffect, useState } from "react";

import {
  Card,
  DataTable,
  ErrorBanner,
  FormField,
  LoadingState,
  PrimaryButton,
  SecondaryButton,
  SelectInput,
  StatCard,
  StatusBadge,
  TextArea,
} from "../../components/ui.jsx";
import { apiClient } from "../../api/client.js";
import { useAuth } from "../../context/AuthContext.jsx";
import { getFriendlyError, useApiResource } from "../../hooks/useAgentPortalData.js";
import { formatDateTime } from "../../utils/formatters.js";
import AdminPageShell from "./AdminPageShell.jsx";

const statusOptions = ["Open", "In Progress", "Waiting for Admin", "Waiting for Agent", "Resolved", "Closed"];

export default function AdminMessagesPage() {
  const { token } = useAuth();
  const tickets = useApiResource("/messages", { initialData: [] });
  const [selectedId, setSelectedId] = useState(null);
  const [reply, setReply] = useState("");
  const [savingReply, setSavingReply] = useState(false);
  const [savingStatus, setSavingStatus] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const rows = tickets.data || [];
  const selectedTicket = rows.find((ticket) => ticket.id === selectedId) || rows[0] || null;
  const openCount = rows.filter((ticket) => !["Resolved", "Closed"].includes(ticket.status)).length;
  const waitingAdminCount = rows.filter((ticket) => ticket.status === "Waiting for Admin" || ticket.status === "Open").length;
  const resolvedCount = rows.filter((ticket) => ["Resolved", "Closed"].includes(ticket.status)).length;

  useEffect(() => {
    if (!selectedId && rows.length) {
      setSelectedId(rows[0].id);
    }
  }, [rows, selectedId]);

  async function sendReply(event) {
    event.preventDefault();
    if (!selectedTicket) return;

    setSavingReply(true);
    setError("");
    setSuccess("");

    try {
      const updated = await apiClient.post(`/messages/${selectedTicket.id}/replies`, { message: reply }, token);
      setReply("");
      await tickets.reload();
      setSelectedId(updated.id);
      setSuccess("Reply sent and the agent has been emailed.");
    } catch (err) {
      setError(getFriendlyError(err, "We could not send this reply."));
    } finally {
      setSavingReply(false);
    }
  }

  async function updateStatus(nextStatus) {
    if (!selectedTicket || nextStatus === selectedTicket.status) return;

    setSavingStatus(true);
    setError("");
    setSuccess("");

    try {
      const updated = await apiClient.put(`/messages/${selectedTicket.id}/status`, { status: nextStatus }, token);
      await tickets.reload();
      setSelectedId(updated.id);
      setSuccess("Status updated and the agent has been emailed.");
    } catch (err) {
      setError(getFriendlyError(err, "We could not update this status."));
    } finally {
      setSavingStatus(false);
    }
  }

  if (tickets.loading) {
    return (
      <AdminPageShell title="Admin Messages" description="Loading message tickets.">
        <LoadingState message="Loading messages..." />
      </AdminPageShell>
    );
  }

  return (
    <AdminPageShell
      title="Admin Messages"
      description="Read agent messages, reply to them, and update ticket status. Replies and status changes email the agent."
      actions={
        <SecondaryButton type="button" icon={RefreshCw} onClick={() => tickets.reload()}>
          Refresh
        </SecondaryButton>
      }
    >
      <div className="space-y-6">
        <ErrorBanner message={tickets.error || error} />
        {success ? <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm font-medium text-emerald-700">{success}</div> : null}

        <div className="grid gap-4 md:grid-cols-3">
          <StatCard label="Open tickets" value={openCount} detail="Still need action or monitoring" icon={MessageSquare} />
          <StatCard label="Waiting for admin" value={waitingAdminCount} detail="New or agent replies" icon={MessageSquare} />
          <StatCard label="Resolved or closed" value={resolvedCount} detail="Completed tickets" icon={MessageSquare} />
        </div>

        <div className="grid gap-6 xl:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
          <Card title="Message Queue" description="Newest messages appear first.">
            <DataTable
              rows={rows}
              emptyMessage="No message tickets yet."
              columns={[
                { key: "agent_name", label: "Agent" },
                { key: "subject", label: "Subject" },
                { key: "status", label: "Status", render: (row) => <StatusBadge status={row.status} /> },
                { key: "last_message_at", label: "Updated", render: (row) => formatDateTime(row.last_message_at) },
                {
                  key: "action",
                  label: "Action",
                  render: (row) => (
                    <SecondaryButton type="button" icon={MessageSquare} onClick={() => setSelectedId(row.id)}>
                      Open
                    </SecondaryButton>
                  ),
                },
              ]}
            />
          </Card>

          <Card title={selectedTicket ? selectedTicket.subject : "Ticket Details"} description={selectedTicket ? `${selectedTicket.agent_name} - ${selectedTicket.agent_email}` : "Open a ticket to manage it."}>
            {selectedTicket ? (
              <div className="space-y-5">
                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <p className="text-sm font-medium text-slate-600">Current status</p>
                    <div className="mt-2">
                      <StatusBadge status={selectedTicket.status} />
                    </div>
                  </div>
                  <FormField label="Update status">
                    <SelectInput value={selectedTicket.status} disabled={savingStatus} onChange={(event) => updateStatus(event.target.value)}>
                      {statusOptions.map((status) => (
                        <option key={status} value={status}>
                          {status}
                        </option>
                      ))}
                    </SelectInput>
                  </FormField>
                </div>

                <MessageThread ticket={selectedTicket} />

                <form onSubmit={sendReply} className="space-y-3 border-t border-slate-200 pt-4">
                  <FormField label="Reply to agent">
                    <TextArea required value={reply} onChange={(event) => setReply(event.target.value)} placeholder="Write your reply..." />
                  </FormField>
                  <PrimaryButton type="submit" icon={Send} disabled={savingReply}>
                    {savingReply ? "Sending..." : "Send reply"}
                  </PrimaryButton>
                </form>
              </div>
            ) : (
              <p className="text-sm text-slate-600">No ticket selected yet.</p>
            )}
          </Card>
        </div>
      </div>
    </AdminPageShell>
  );
}

function MessageThread({ ticket }) {
  return (
    <div className="space-y-3">
      {ticket.messages.map((item) => (
        <div key={item.id} className="rounded-lg border border-slate-200 bg-slate-50 p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-sm font-semibold text-slate-950">
              {item.sender_role === "Agent" ? ticket.agent_name : item.sender_role}
            </p>
            <p className="text-xs text-slate-500">{formatDateTime(item.created_at)}</p>
          </div>
          <p className="mt-2 whitespace-pre-wrap text-sm text-slate-700">{item.message}</p>
        </div>
      ))}
    </div>
  );
}
