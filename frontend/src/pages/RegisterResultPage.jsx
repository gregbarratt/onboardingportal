import { AlertCircle, CheckCircle2, LogIn, RotateCcw } from "lucide-react";
import { Link, useLocation } from "react-router-dom";

export default function RegisterResultPage({ status }) {
  const location = useLocation();
  const sessionId = new URLSearchParams(location.search).get("session_id");
  const success = status === "success";

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-100 px-4 py-10">
      <section className="w-full max-w-lg rounded-lg border border-slate-200 bg-white p-7 text-center shadow-soft">
        <div className={`mx-auto flex h-12 w-12 items-center justify-center rounded-lg ${success ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"}`}>
          {success ? <CheckCircle2 size={24} /> : <AlertCircle size={24} />}
        </div>
        <h1 className="mt-5 text-xl font-bold text-ink">
          {success ? "Payment Submitted" : "Payment Not Completed"}
        </h1>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          {success
            ? "Stripe has received the payment setup. The portal will unlock your account once Stripe confirms the payment and subscription."
            : "Your registration has not been completed because the Stripe payment setup was cancelled."}
        </p>
        {sessionId ? <p className="mt-3 text-xs text-slate-500">Stripe session: {sessionId}</p> : null}
        <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:justify-center">
          <Link className="focus-ring inline-flex items-center justify-center gap-2 rounded-lg bg-sea px-4 py-2.5 text-sm font-bold text-white hover:bg-teal-800" to="/login">
            <LogIn size={18} />
            Go to sign in
          </Link>
          {!success ? (
            <Link className="focus-ring inline-flex items-center justify-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm font-bold text-slate-700 hover:bg-slate-50" to="/register">
              <RotateCcw size={18} />
              Start again
            </Link>
          ) : null}
        </div>
      </section>
    </main>
  );
}
