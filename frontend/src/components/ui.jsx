import {
  AlertCircle,
  CheckCircle2,
  FileText,
  Lock,
  Plus,
  RefreshCw,
} from "lucide-react";

const statusToneMap = {
  active: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  approved: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  complete: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  paid: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  verified: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  pending: "bg-amber-50 text-amber-700 ring-amber-200",
  progress: "bg-sky-50 text-sky-700 ring-sky-200",
  review: "bg-indigo-50 text-indigo-700 ring-indigo-200",
  overdue: "bg-rose-50 text-rose-700 ring-rose-200",
  failed: "bg-rose-50 text-rose-700 ring-rose-200",
  suspended: "bg-rose-50 text-rose-700 ring-rose-200",
  rejected: "bg-rose-50 text-rose-700 ring-rose-200",
  archived: "bg-slate-100 text-slate-600 ring-slate-200",
  default: "bg-slate-100 text-slate-700 ring-slate-200",
};

export function getStatusTone(status = "") {
  const value = status.toLowerCase();

  if (value.includes("active")) return statusToneMap.active;
  if (value.includes("approved")) return statusToneMap.approved;
  if (value.includes("complete")) return statusToneMap.complete;
  if (value.includes("paid")) return statusToneMap.paid;
  if (value.includes("verified")) return statusToneMap.verified;
  if (value.includes("pending")) return statusToneMap.pending;
  if (value.includes("progress")) return statusToneMap.progress;
  if (value.includes("review") || value.includes("awaiting")) return statusToneMap.review;
  if (value.includes("overdue")) return statusToneMap.overdue;
  if (value.includes("failed")) return statusToneMap.failed;
  if (value.includes("suspended") || value.includes("hold")) return statusToneMap.suspended;
  if (value.includes("rejected")) return statusToneMap.rejected;
  if (value.includes("archived") || value.includes("cancelled")) return statusToneMap.archived;

  return statusToneMap.default;
}

export function PageHeader({ eyebrow, title, description, actions }) {
  return (
    <div className="flex flex-col gap-4 border-b border-slate-200 pb-6 lg:flex-row lg:items-end lg:justify-between">
      <div>
        {eyebrow ? (
          <p className="text-xs font-semibold uppercase tracking-wide text-sky-700">{eyebrow}</p>
        ) : null}
        <h1 className="mt-2 text-2xl font-semibold text-slate-950">{title}</h1>
        {description ? <p className="mt-2 max-w-3xl text-sm text-slate-600">{description}</p> : null}
      </div>
      {actions ? <div className="flex flex-wrap gap-2">{actions}</div> : null}
    </div>
  );
}

export function Card({ title, description, actions, children, className = "" }) {
  return (
    <section className={`rounded-lg border border-slate-200 bg-white p-5 shadow-sm ${className}`}>
      {(title || description || actions) && (
        <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            {title ? <h2 className="text-base font-semibold text-slate-950">{title}</h2> : null}
            {description ? <p className="mt-1 text-sm text-slate-600">{description}</p> : null}
          </div>
          {actions ? <div className="flex shrink-0 flex-wrap gap-2">{actions}</div> : null}
        </div>
      )}
      {children}
    </section>
  );
}

export function StatCard({ label, value, detail, icon: Icon = CheckCircle2 }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-slate-600">{label}</p>
          <p className="mt-2 text-2xl font-semibold text-slate-950">{value}</p>
        </div>
        <span className="rounded-lg bg-sky-50 p-2 text-sky-700">
          <Icon className="h-5 w-5" aria-hidden="true" />
        </span>
      </div>
      {detail ? <p className="mt-3 text-sm text-slate-500">{detail}</p> : null}
    </div>
  );
}

export function StatusBadge({ status }) {
  if (!status) {
    return <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ring-1 ${statusToneMap.default}`}>Not set</span>;
  }

  return (
    <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ring-1 ${getStatusTone(status)}`}>
      {status}
    </span>
  );
}

export function ProgressBar({ value = 0, label }) {
  const safeValue = Math.min(100, Math.max(0, Number.isFinite(value) ? value : 0));

  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-sm">
        <span className="font-medium text-slate-700">{label || "Progress"}</span>
        <span className="text-slate-500">{safeValue}%</span>
      </div>
      <div className="h-2 rounded-full bg-slate-100">
        <div className="h-2 rounded-full bg-sky-600" style={{ width: `${safeValue}%` }} />
      </div>
    </div>
  );
}

export function DataTable({ columns, rows, emptyMessage = "There is nothing to show yet." }) {
  if (!rows?.length) {
    return <EmptyState message={emptyMessage} />;
  }

  return (
    <div className="overflow-hidden rounded-lg border border-slate-200">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-200 text-sm">
          <thead className="bg-slate-50">
            <tr>
              {columns.map((column) => (
                <th key={column.key} scope="col" className="px-4 py-3 text-left font-semibold text-slate-700">
                  {column.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white">
            {rows.map((row) => (
              <tr key={row.id || JSON.stringify(row)} className="align-top">
                {columns.map((column) => (
                  <td key={column.key} className="px-4 py-3 text-slate-700">
                    {column.render ? column.render(row) : row[column.key] === null || row[column.key] === undefined || row[column.key] === "" ? "Not set" : row[column.key]}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function EmptyState({ title = "Nothing here yet", message = "This area will fill up as the portal is used.", icon: Icon = FileText }) {
  return (
    <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 px-4 py-8 text-center">
      <Icon className="mx-auto h-8 w-8 text-slate-400" aria-hidden="true" />
      <h3 className="mt-3 text-sm font-semibold text-slate-900">{title}</h3>
      <p className="mx-auto mt-1 max-w-md text-sm text-slate-600">{message}</p>
    </div>
  );
}

export function LoadingState({ message = "Loading this page..." }) {
  return (
    <div className="flex min-h-40 items-center justify-center rounded-lg border border-slate-200 bg-white p-6 text-sm text-slate-600">
      <RefreshCw className="mr-2 h-4 w-4 animate-spin text-sky-700" aria-hidden="true" />
      {message}
    </div>
  );
}

export function ErrorBanner({ message }) {
  if (!message) return null;

  return (
    <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
      <div className="flex gap-2">
        <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
        <p>{message}</p>
      </div>
    </div>
  );
}

export function LockNotice({ title = "This section is locked", message }) {
  return (
    <div className="rounded-lg border border-amber-200 bg-amber-50 p-5 text-amber-800">
      <div className="flex gap-3">
        <Lock className="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" />
        <div>
          <h3 className="font-semibold">{title}</h3>
          {message ? <p className="mt-1 text-sm">{message}</p> : null}
        </div>
      </div>
    </div>
  );
}

export function FormField({ label, children, help }) {
  return (
    <label className="block">
      <span className="text-sm font-medium text-slate-700">{label}</span>
      <div className="mt-1">{children}</div>
      {help ? <span className="mt-1 block text-xs text-slate-500">{help}</span> : null}
    </label>
  );
}

export function TextInput(props) {
  return (
    <input
      {...props}
      className={`w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 shadow-sm outline-none transition focus:border-sky-600 focus:ring-2 focus:ring-sky-100 ${props.className || ""}`}
    />
  );
}

export function TextArea(props) {
  return (
    <textarea
      {...props}
      className={`min-h-24 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 shadow-sm outline-none transition focus:border-sky-600 focus:ring-2 focus:ring-sky-100 ${props.className || ""}`}
    />
  );
}

export function SelectInput({ children, ...props }) {
  return (
    <select
      {...props}
      className={`w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 shadow-sm outline-none transition focus:border-sky-600 focus:ring-2 focus:ring-sky-100 ${props.className || ""}`}
    >
      {children}
    </select>
  );
}

export function PrimaryButton({ children, icon: Icon = Plus, ...props }) {
  return (
    <button
      {...props}
      className={`inline-flex items-center justify-center gap-2 rounded-lg bg-sky-700 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-sky-800 disabled:cursor-not-allowed disabled:bg-slate-300 ${props.className || ""}`}
    >
      {Icon ? <Icon className="h-4 w-4" aria-hidden="true" /> : null}
      {children}
    </button>
  );
}

export function SecondaryButton({ children, icon: Icon, ...props }) {
  return (
    <button
      {...props}
      className={`inline-flex items-center justify-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:text-slate-400 ${props.className || ""}`}
    >
      {Icon ? <Icon className="h-4 w-4" aria-hidden="true" /> : null}
      {children}
    </button>
  );
}
