import { MessageSquare, Send } from "lucide-react";
import { useEffect, useState } from "react";

import {
  Card,
  DataTable,
  ErrorBanner,
  FormField,
  LoadingState,
  PrimaryButton,
  SecondaryButton,
  StatusBadge,
  TextArea,
  TextInput,
} from "../../components/ui.jsx";
import { apiClient } from "../../api/client.js";
import { useAuth } from "../../context/AuthContext.jsx";
import { getFriendlyError, useApiResource } from "../../hooks/useAgentPortalData.js";
import { formatDateTime } from "../../utils/formatters.js";
import AgentPageShell from "./AgentPageShell.jsx";

export default function MessagesPage() {
  return (
    <AgentPageShell
      title="Messages"
      description="Send a written message to the One Travel Club team and keep track of replies."
    >
      {() => <MessagesContent />}
    </AgentPageShell>
  );
}

function MessagesContent() {
  const { token } = useAuth();
  const tickets = useApiResource("/messages", { initialData: [] });
  const [selectedId, setSelectedId] = useState(null);
  const [subject, setSubject] = useState("");
  const [message, setMessage] = useState("");
  const [reply, setReply] = useState("");
  const [saving, setSaving] = useState(false);
  const [replying, setReplying] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const rows = tickets.data || [];
  const selectedTicket = rows.find((ticket) => ticket.id === selectedId) || rows[0] || null;

  useEffect(() => {
    if (!selectedId && rows.length) {
      setSelectedId(rows[0].id);
    }
  }, [rows, selectedId]);

  async function createTicket(event) {
    event.preventDefault();
    setSaving(true);
    setError("");
    setSuccess("");

    try {
      const created = await apiClient.post("/messages", { subject, message }, token);
      setSubject("");
      setMessage("");
      await tickets.reload();
      setSelectedId(created.id);
      setSuccess("Message sent to the admin team.");
    } catch (err) {
      setError(getFriendlyError(err, "We could not send this message."));
    } finally {
      setSaving(false);
    }
  }

  async function sendReply(event) {
    event.preventDefault();
    if (!selectedTicket) return;

    setReplying(true);
    setError("");
    setSuccess("");

    try {
      const updated = await apiClient.post(`/messages/${selectedTicket.id}/replies`, { message: reply }, token);
      setReply("");
      await tickets.reload();
      setSelectedId(updated.id);
      setSuccess("Reply sent.");
    } catch (err) {
      setError(getFriendlyError(err, "We could not send this reply."));
    } finally {
      setReplying(false);
    }
  }

  if (tickets.loading) {
    return <LoadingState message="Loading messages..." />;
  }

  return (
    <div className="space-y-6">
      <ErrorBanner message={tickets.error || error} />
      {success ? <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm font-medium text-emerald-700">{success}</div> : null}

      <Card title="Send a New Message" description="This creates a ticket for the admin team and emails Accounts.">
        <form onSubmit={createTicket} className="space-y-4">
          <FormField label="Subject">
            <TextInput required maxLength={255} value={subject} onChange={(event) => setSubject(event.target.value)} placeholder="What do you need help with?" />
          </FormField>
          <FormField label="Message">
            <TextArea required value={message} onChange={(event) => setMessage(event.target.value)} placeholder="Write your message here..." />
          </FormField>
          <PrimaryButton type="submit" icon={Send} disabled={saving}>
            {saving ? "Sending..." : "Send message"}
          </PrimaryButton>
        </form>
      </Card>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
        <Card title="My Tickets">
          <DataTable
            rows={rows}
            emptyMessage="You have not sent any messages yet."
            columns={[
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

        <Card title={selectedTicket ? selectedTicket.subject : "Message Thread"} description={selectedTicket ? `Status: ${selectedTicket.status}` : "Open a ticket to see the conversation."}>
          {selectedTicket ? (
            <div className="space-y-4">
              <MessageThread ticket={selectedTicket} />
              <form onSubmit={sendReply} className="space-y-3 border-t border-slate-200 pt-4">
                <FormField label="Reply">
                  <TextArea required value={reply} onChange={(event) => setReply(event.target.value)} placeholder="Add a reply..." />
                </FormField>
                <PrimaryButton type="submit" icon={Send} disabled={replying}>
                  {replying ? "Sending..." : "Send reply"}
                </PrimaryButton>
              </form>
            </div>
          ) : (
            <p className="text-sm text-slate-600">No message thread selected yet.</p>
          )}
        </Card>
      </div>
    </div>
  );
}

function MessageThread({ ticket }) {
  return (
    <div className="space-y-3">
      {ticket.messages.map((item) => (
        <div key={item.id} className="rounded-lg border border-slate-200 bg-slate-50 p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-sm font-semibold text-slate-950">{item.sender_role === "Agent" ? "You" : item.sender_role}</p>
            <p className="text-xs text-slate-500">{formatDateTime(item.created_at)}</p>
          </div>
          <p className="mt-2 whitespace-pre-wrap text-sm text-slate-700">{item.message}</p>
        </div>
      ))}
    </div>
  );
}
