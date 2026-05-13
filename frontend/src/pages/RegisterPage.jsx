import { ArrowRight, CheckCircle2, Loader2, LockKeyhole } from "lucide-react";
import { useState } from "react";
import { Link, Navigate } from "react-router-dom";

import { apiClient } from "../api/client.js";
import { useAuth } from "../context/AuthContext.jsx";

const blankForm = {
  first_name: "",
  last_name: "",
  email: "",
  password: "",
  confirm_password: "",
  phone: "",
  business_name: "",
  address: "",
  postcode: "",
  accepted_terms: false,
};

export default function RegisterPage() {
  const { isAuthenticated } = useAuth();
  const [form, setForm] = useState(blankForm);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  function update(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");

    if (form.password !== form.confirm_password) {
      setError("Passwords do not match.");
      return;
    }

    setSubmitting(true);
    try {
      const response = await apiClient.post("/auth/register-agent", {
        first_name: form.first_name,
        last_name: form.last_name,
        email: form.email,
        password: form.password,
        phone: form.phone,
        business_name: form.business_name,
        address: form.address,
        postcode: form.postcode,
        accepted_terms: form.accepted_terms,
      });
      window.location.assign(response.checkout_url);
    } catch (registrationError) {
      setError(registrationError.message || "Registration could not be completed.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="min-h-screen bg-slate-100 px-4 py-10">
      <section className="mx-auto w-full max-w-5xl rounded-lg border border-slate-200 bg-white p-6 shadow-soft md:p-8">
        <div className="mb-7 flex flex-col gap-4 border-b border-slate-200 pb-6 md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-sea text-white">
              <LockKeyhole size={21} />
            </div>
            <div>
              <h1 className="text-xl font-bold text-ink">Apply To Join One Travel Club</h1>
              <p className="text-sm text-slate-500">Create your portal account, then continue to secure Stripe payment.</p>
            </div>
          </div>
          <Link className="text-sm font-semibold text-sky-700 hover:text-sky-900" to="/login">
            Already registered? Sign in
          </Link>
        </div>

        <form className="space-y-6" onSubmit={handleSubmit}>
          <div className="grid gap-4 md:grid-cols-2">
            <FormInput label="First name" value={form.first_name} onChange={(value) => update("first_name", value)} required />
            <FormInput label="Last name" value={form.last_name} onChange={(value) => update("last_name", value)} required />
            <FormInput label="Personal email" type="email" value={form.email} onChange={(value) => update("email", value)} required />
            <FormInput label="Mobile number" value={form.phone} onChange={(value) => update("phone", value)} required />
            <FormInput label="Business name" value={form.business_name} onChange={(value) => update("business_name", value)} />
            <FormInput label="Postcode" value={form.postcode} onChange={(value) => update("postcode", value)} required />
            <div className="md:col-span-2">
              <label className="block">
                <span className="mb-1.5 block text-sm font-semibold text-slate-700">Address</span>
                <textarea
                  className="focus-ring min-h-24 w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm text-ink"
                  value={form.address}
                  onChange={(event) => update("address", event.target.value)}
                  required
                />
              </label>
            </div>
            <FormInput label="Password" type="password" value={form.password} onChange={(value) => update("password", value)} required />
            <FormInput label="Confirm password" type="password" value={form.confirm_password} onChange={(value) => update("confirm_password", value)} required />
          </div>

          <label className="flex items-start gap-3 rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={form.accepted_terms}
              onChange={(event) => update("accepted_terms", event.target.checked)}
              className="mt-0.5 h-4 w-4 rounded border-slate-300 text-sea focus:ring-sea"
              required
            />
            <span>
              I confirm the details are correct and I agree to continue to Stripe to set up the required One Travel Club membership payment.
            </span>
          </label>

          {error ? (
            <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm font-medium text-red-700">
              {error}
            </div>
          ) : null}

          <div className="flex flex-col gap-3 border-t border-slate-200 pt-5 md:flex-row md:items-center md:justify-between">
            <div className="flex items-start gap-2 text-sm text-slate-600">
              <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" aria-hidden="true" />
              <span>Card details are entered only on Stripe. They are not stored in this portal.</span>
            </div>
            <button
              type="submit"
              disabled={submitting}
              className="focus-ring inline-flex items-center justify-center gap-2 rounded-lg bg-sea px-5 py-2.5 text-sm font-bold text-white hover:bg-teal-800 disabled:cursor-not-allowed disabled:opacity-70"
            >
              {submitting ? <Loader2 className="animate-spin" size={18} /> : <ArrowRight size={18} />}
              Continue to secure payment
            </button>
          </div>
        </form>
      </section>
    </main>
  );
}

function FormInput({ label, value, onChange, type = "text", required = false }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-sm font-semibold text-slate-700">{label}</span>
      <input
        className="focus-ring w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm text-ink"
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        required={required}
      />
    </label>
  );
}
