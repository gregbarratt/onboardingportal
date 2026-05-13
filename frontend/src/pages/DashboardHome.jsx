import { Bell, CheckCircle2, Clock3, ShieldCheck } from "lucide-react";

import { useAuth } from "../context/AuthContext.jsx";

const stats = [
  { label: "Onboarding", value: "In progress", icon: Clock3, tone: "bg-amber-50 text-amber-700" },
  { label: "Training", value: "Ready", icon: CheckCircle2, tone: "bg-emerald-50 text-emerald-700" },
  { label: "Compliance", value: "Tracked", icon: ShieldCheck, tone: "bg-blue-50 text-blue-700" },
  { label: "Notifications", value: "Live", icon: Bell, tone: "bg-orange-50 text-coral" },
];

export default function DashboardHome() {
  const { user } = useAuth();

  return (
    <div className="space-y-6">
      <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-soft">
        <p className="text-sm font-semibold text-sea">{user?.role?.name || "Portal user"}</p>
        <h1 className="mt-1 text-2xl font-bold text-ink">Welcome back</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">{user?.email}</p>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {stats.map((item) => {
          const Icon = item.icon;
          return (
            <article key={item.label} className="rounded-lg border border-slate-200 bg-white p-5 shadow-soft">
              <div className={`mb-4 inline-flex h-10 w-10 items-center justify-center rounded-lg ${item.tone}`}>
                <Icon size={20} />
              </div>
              <p className="text-sm font-medium text-slate-500">{item.label}</p>
              <p className="mt-1 text-lg font-bold text-ink">{item.value}</p>
            </article>
          );
        })}
      </section>
    </div>
  );
}
