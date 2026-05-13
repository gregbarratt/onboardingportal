import { Link } from "react-router-dom";

import { PageHeader } from "../../components/ui.jsx";

export default function AdminPageShell({ title, description, actions, children }) {
  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Admin" title={title} description={description} actions={actions} />
      {children}
    </div>
  );
}

export function AdminLinkButton({ to, children }) {
  return (
    <Link
      to={to}
      className="inline-flex items-center justify-center rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50"
    >
      {children}
    </Link>
  );
}
