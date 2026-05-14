import { ArrowLeft, ArrowRight, CheckCircle2, Loader2, LockKeyhole } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { apiClient } from "../api/client.js";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [resetUrl, setResetUrl] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    setMessage("");
    setResetUrl("");

    try {
      const response = await apiClient.post("/auth/password-reset/request", { email });
      setMessage(response.message || "If this email belongs to a portal account, password reset instructions will be sent.");
      setResetUrl(response.reset_url || "");
    } catch (err) {
      setError(err.message || "Password reset could not be started.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-100 px-4 py-10">
      <section className="w-full max-w-md rounded-lg border border-slate-200 bg-white p-7 shadow-soft">
        <div className="mb-7 flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-sea text-white">
            <LockKeyhole size={21} />
          </div>
          <div>
            <h1 className="text-xl font-bold text-ink">Reset your password</h1>
            <p className="text-sm text-slate-500">One Travel Club secure portal</p>
          </div>
        </div>

        {message ? (
          <div className="mb-5 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-3 text-sm text-emerald-700">
            <div className="flex gap-2">
              <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
              <p>{message}</p>
            </div>
            {resetUrl ? (
              <a className="mt-3 inline-flex items-center gap-2 font-semibold text-sky-700 hover:text-sky-900" href={resetUrl}>
                Open reset page <ArrowRight size={16} />
              </a>
            ) : null}
          </div>
        ) : null}

        <form className="space-y-5" onSubmit={handleSubmit}>
          <label className="block">
            <span className="mb-1.5 block text-sm font-semibold text-slate-700">Email</span>
            <input
              className="focus-ring w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm text-ink"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              autoComplete="email"
              required
            />
          </label>

          {error ? (
            <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm font-medium text-red-700">
              {error}
            </div>
          ) : null}

          <button
            type="submit"
            disabled={submitting}
            className="focus-ring inline-flex w-full items-center justify-center gap-2 rounded-lg bg-sea px-4 py-2.5 text-sm font-bold text-white hover:bg-teal-800 disabled:cursor-not-allowed disabled:opacity-70"
          >
            {submitting ? <Loader2 className="animate-spin" size={18} /> : <ArrowRight size={18} />}
            Send reset instructions
          </button>
        </form>

        <p className="mt-5 text-center text-sm text-slate-600">
          <Link className="inline-flex items-center gap-2 font-semibold text-sky-700 hover:text-sky-900" to="/login">
            <ArrowLeft size={16} /> Back to sign in
          </Link>
        </p>
      </section>
    </main>
  );
}
