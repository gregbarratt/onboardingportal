import { Link } from "react-router-dom";

export default function NotFoundPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-100 px-4">
      <section className="w-full max-w-md rounded-lg border border-slate-200 bg-white p-7 text-center shadow-soft">
        <h1 className="text-2xl font-bold text-ink">Page not found</h1>
        <p className="mt-3 text-sm text-slate-600">The page you asked for is not available.</p>
        <Link
          to="/dashboard"
          className="focus-ring mt-5 inline-flex rounded-lg bg-sea px-4 py-2 text-sm font-bold text-white hover:bg-teal-800"
        >
          Go to dashboard
        </Link>
      </section>
    </main>
  );
}
