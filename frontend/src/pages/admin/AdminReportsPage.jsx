import { BarChart3, CalendarX, CreditCard, FileWarning, GraduationCap, ShieldAlert, UserCheck } from "lucide-react";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import {
  Card,
  DataTable,
  ErrorBanner,
  FormField,
  LoadingState,
  ProgressBar,
  SelectInput,
  StatCard,
  StatusBadge,
  TextInput,
} from "../../components/ui.jsx";
import { useApiResource } from "../../hooks/useAgentPortalData.js";
import { compactList, formatDate } from "../../utils/formatters.js";
import AdminPageShell from "./AdminPageShell.jsx";

const emptyReports = {
  agents_by_status: [],
  payment_status_report: [],
  training_completion_report: [],
  overdue_training_report: [],
  attendance_report: [],
  compliance_expiry_report: [],
  documents_awaiting_review: [],
  final_approval_queue: [],
};

export default function AdminReportsPage() {
  const reports = useApiResource("/admin/reports", {
    initialData: emptyReports,
    fallbackError: "We could not load admin reports.",
  });
  const [search, setSearch] = useState("");
  const [paymentStatus, setPaymentStatus] = useState("All");
  const [attendanceStatus, setAttendanceStatus] = useState("All");

  const data = reports.data || emptyReports;
  const filtered = useMemo(() => {
    const bySearch = (row) => matchesSearch(row, search);
    return {
      paymentRows: data.payment_status_report.filter((row) => bySearch(row) && matchesValue(row.payment_status, paymentStatus)),
      trainingRows: data.training_completion_report.filter(bySearch),
      overdueRows: data.overdue_training_report.filter(bySearch),
      attendanceRows: data.attendance_report.filter((row) => bySearch(row) && matchesValue(row.attendance_status, attendanceStatus)),
      expiryRows: data.compliance_expiry_report.filter(bySearch),
      documentRows: data.documents_awaiting_review.filter(bySearch),
      approvalRows: data.final_approval_queue.filter(bySearch),
    };
  }, [attendanceStatus, data, paymentStatus, search]);

  if (reports.loading) {
    return (
      <AdminPageShell title="Reports" description="Loading admin reports.">
        <LoadingState message="Loading reports..." />
      </AdminPageShell>
    );
  }

  return (
    <AdminPageShell title="Reports" description="Simple admin reports for agents, payments, training, attendance, compliance, documents, and final approval.">
      <div className="space-y-6">
        <ErrorBanner message={reports.error} />

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Payment rows" value={filtered.paymentRows.length} icon={CreditCard} />
          <StatCard label="Overdue training" value={filtered.overdueRows.length} icon={CalendarX} />
          <StatCard label="Review documents" value={filtered.documentRows.length} icon={FileWarning} />
          <StatCard label="Final approval" value={filtered.approvalRows.length} icon={UserCheck} />
        </div>

        <Card title="Report Filters" description="Use these filters to narrow the report tables below.">
          <div className="grid gap-4 md:grid-cols-3">
            <FormField label="Search agent">
              <TextInput value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Type an agent name" />
            </FormField>
            <FormField label="Payment status">
              <SelectInput value={paymentStatus} onChange={(event) => setPaymentStatus(event.target.value)}>
                {buildOptions(data.payment_status_report, "payment_status").map((option) => (
                  <option key={option} value={option}>{option}</option>
                ))}
              </SelectInput>
            </FormField>
            <FormField label="Attendance status">
              <SelectInput value={attendanceStatus} onChange={(event) => setAttendanceStatus(event.target.value)}>
                {buildOptions(data.attendance_report, "attendance_status").map((option) => (
                  <option key={option} value={option}>{option}</option>
                ))}
              </SelectInput>
            </FormField>
          </div>
        </Card>

        <div className="grid gap-6 xl:grid-cols-[0.8fr_1.2fr]">
          <Card title="Agents by Status" description="A quick count of agents in each status.">
            <DataTable
              rows={data.agents_by_status}
              emptyMessage="No agent status data yet."
              columns={[
                { key: "status", label: "Status", render: (row) => <StatusBadge status={row.status} /> },
                { key: "total", label: "Total" },
              ]}
            />
          </Card>

          <ReportCard title="Final Approval Queue" description="Agents waiting for the final approval decision.">
            <DataTable
              rows={filtered.approvalRows}
              emptyMessage="No agents are waiting for final approval."
              columns={[
                { key: "agent_name", label: "Agent", render: (row) => <AgentLink row={row} /> },
                { key: "agent_status", label: "Status", render: (row) => <StatusBadge status={row.agent_status} /> },
                { key: "ready_for_approval", label: "Ready", render: (row) => (row.ready_for_approval ? "Yes" : "No") },
                { key: "missing_requirements", label: "Missing", render: (row) => compactList(row.missing_requirements, "Nothing missing") },
              ]}
            />
          </ReportCard>
        </div>

        <ReportCard title="Payment Status Report" description="Membership payment position by agent.">
          <DataTable
            rows={filtered.paymentRows}
            emptyMessage="No payment rows match the current filters."
            columns={[
              { key: "agent_name", label: "Agent", render: (row) => <AgentLink row={row} /> },
              { key: "membership_status", label: "Membership", render: (row) => <StatusBadge status={row.membership_status} /> },
              { key: "payment_status", label: "Payment", render: (row) => <StatusBadge status={row.payment_status} /> },
              { key: "next_payment_date", label: "Next payment", render: (row) => formatDate(row.next_payment_date) },
              { key: "failed_payment_count", label: "Failed" },
            ]}
          />
        </ReportCard>

        <ReportCard title="Training Completion Report" description="Mandatory onboarding training progress by agent.">
          <DataTable
            rows={filtered.trainingRows}
            emptyMessage="No training rows match the current filters."
            columns={[
              { key: "agent_name", label: "Agent", render: (row) => <AgentLink row={row} /> },
              { key: "agent_status", label: "Status", render: (row) => <StatusBadge status={row.agent_status} /> },
              { key: "completed_mandatory_modules", label: "Completed", render: (row) => `${row.completed_mandatory_modules}/${row.total_mandatory_modules}` },
              { key: "completion_percent", label: "Progress", render: (row) => <ProgressBar value={row.completion_percent} label="Training" /> },
              { key: "failed_modules", label: "Failed" },
            ]}
          />
        </ReportCard>

        <div className="grid gap-6 xl:grid-cols-2">
          <ReportCard title="Overdue Training Report" description="Assigned training with a due date in the past.">
            <DataTable
              rows={filtered.overdueRows}
              emptyMessage="No overdue training matches the current filters."
              columns={[
                { key: "agent_name", label: "Agent", render: (row) => <AgentLink row={row} /> },
                { key: "module_title", label: "Module" },
                { key: "due_date", label: "Due", render: (row) => formatDate(row.due_date) },
                { key: "days_overdue", label: "Days overdue" },
                { key: "progress_status", label: "Status", render: (row) => <StatusBadge status={row.progress_status} /> },
              ]}
            />
          </ReportCard>

          <ReportCard title="Attendance Report" description="Recent live call attendance and follow-up needs.">
            <DataTable
              rows={filtered.attendanceRows}
              emptyMessage="No attendance rows match the current filters."
              columns={[
                { key: "agent_name", label: "Agent", render: (row) => <AgentLink row={row} /> },
                { key: "session_type", label: "Type" },
                { key: "session_date", label: "Date", render: (row) => formatDate(row.session_date) },
                { key: "attendance_status", label: "Status", render: (row) => <StatusBadge status={row.attendance_status} /> },
                { key: "follow_up_required", label: "Follow-up", render: (row) => (row.follow_up_required ? "Yes" : "No") },
              ]}
            />
          </ReportCard>
        </div>

        <div className="grid gap-6 xl:grid-cols-2">
          <ReportCard title="Compliance Expiry Report" description="Certificates and documents that have expired or are expiring soon.">
            <DataTable
              rows={filtered.expiryRows}
              emptyMessage="No compliance expiry rows match the current filters."
              columns={[
                { key: "agent_name", label: "Agent", render: (row) => <AgentLink row={row} /> },
                { key: "item_type", label: "Type" },
                { key: "item_name", label: "Item" },
                { key: "expiry_date", label: "Expiry", render: (row) => formatDate(row.expiry_date) },
                { key: "status", label: "Status", render: (row) => <StatusBadge status={row.status} /> },
              ]}
            />
          </ReportCard>

          <ReportCard title="Documents Awaiting Review" description="Uploaded documents that still need an admin decision.">
            <DataTable
              rows={filtered.documentRows}
              emptyMessage="No documents are waiting for review."
              columns={[
                { key: "agent_name", label: "Agent", render: (row) => <AgentLink row={row} /> },
                { key: "document_type", label: "Document" },
                { key: "file_name", label: "File" },
                { key: "uploaded_date", label: "Uploaded", render: (row) => formatDate(row.uploaded_date) },
                { key: "status", label: "Status", render: (row) => <StatusBadge status={row.status} /> },
              ]}
            />
          </ReportCard>
        </div>
      </div>
    </AdminPageShell>
  );
}

function ReportCard({ title, description, children }) {
  return <Card title={title} description={description}>{children}</Card>;
}

function AgentLink({ row }) {
  return (
    <Link to={`/admin/agents/${row.agent_id}`} className="font-semibold text-sky-700 hover:text-sky-900">
      {row.agent_name}
    </Link>
  );
}

function matchesSearch(row, search) {
  if (!search.trim()) return true;
  const needle = search.trim().toLowerCase();
  return [row.agent_name, row.agent_status, row.payment_status, row.attendance_status, row.module_title, row.document_type]
    .filter(Boolean)
    .some((value) => String(value).toLowerCase().includes(needle));
}

function matchesValue(value, selected) {
  return selected === "All" || value === selected;
}

function buildOptions(rows, key) {
  const values = Array.from(new Set(rows.map((row) => row[key]).filter(Boolean))).sort();
  return ["All", ...values];
}
