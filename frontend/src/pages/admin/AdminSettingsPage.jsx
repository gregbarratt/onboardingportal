import { Card, StatusBadge } from "../../components/ui.jsx";
import AdminPageShell from "./AdminPageShell.jsx";

export default function AdminSettingsPage() {
  return (
    <AdminPageShell title="Settings" description="A simple admin reference area for portal rules and future setup items.">
      <div className="grid gap-6 xl:grid-cols-2">
        <Card title="Current Portal Rules">
          <dl className="space-y-4 text-sm">
            <Rule label="Supplier access" value="Locked until Approved to Trade" />
            <Rule label="Marketing hub" value="Locked until social media policy is accepted" />
            <Rule label="Further training" value="Locked until mandatory onboarding training is complete" />
            <Rule label="Payment charging" value="Manual tracking only until Stripe keys are added" />
          </dl>
        </Card>

        <Card title="Future Settings">
          <div className="space-y-3 text-sm text-slate-700">
            <Setting label="Stripe live payments" status="Future phase" />
            <Setting label="Email sending" status="Future phase" />
            <Setting label="File storage" status="Future phase" />
            <Setting label="Deployment" status="Future phase" />
          </div>
        </Card>

        <Card title="Admin Role Reminder">
          <p className="text-sm leading-6 text-slate-700">
            Super Admin, Admin, Training Manager, and Compliance Manager can access admin pages. Agents only see their own agent portal pages.
          </p>
        </Card>
      </div>
    </AdminPageShell>
  );
}

function Rule({ label, value }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <dt className="font-medium text-slate-700">{label}</dt>
      <dd className="text-right text-slate-600">{value}</dd>
    </div>
  );
}

function Setting({ label, status }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-lg border border-slate-200 p-3">
      <span className="font-medium text-slate-900">{label}</span>
      <StatusBadge status={status} />
    </div>
  );
}
