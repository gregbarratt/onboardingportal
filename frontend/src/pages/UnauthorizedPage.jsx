import { ShieldAlert } from "lucide-react";
import { Link } from "react-router-dom";

export default function UnauthorizedPage() {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-soft">
      <div className="mb-4 inline-flex h-11 w-11 items-center justify-center rounded-lg bg-red-50 text-red-700">
        <ShieldAlert size={22} />
      </div>
      <h1 className="text-2xl font-bold text-ink">Access restricted</h1>
      <p className="mt-3 max-w-xl text-sm leading-6 text-slate-600">
        Your login does not have permission to view this area.
      </p>
      <Link
        to="/dashboard"
        className="focus-ring mt-5 inline-flex rounded-lg bg-sea px-4 py-2 text-sm font-bold text-white hover:bg-teal-800"
      >
        Back to dashboard
      </Link>
    </section>
  );
}
