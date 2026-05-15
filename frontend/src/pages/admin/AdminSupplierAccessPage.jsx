import { Pencil, Plus, X } from "lucide-react";
import { useMemo, useState } from "react";

import { apiClient } from "../../api/client.js";
import { Card, DataTable, ErrorBanner, FormField, LoadingState, PrimaryButton, SecondaryButton, SelectInput, StatusBadge, TextArea, TextInput } from "../../components/ui.jsx";
import { useAuth } from "../../context/AuthContext.jsx";
import { getFriendlyError, useApiResource } from "../../hooks/useAgentPortalData.js";
import AdminPageShell from "./AdminPageShell.jsx";

const supplierTypes = [
  "Tour Operator",
  "Cruise",
  "Flight Supplier",
  "Hotel Supplier",
  "Transfer Supplier",
  "Insurance",
  "Ancillary",
];

const blankSupplier = {
  supplier_name: "",
  supplier_type: "Tour Operator",
  portal_url: "",
  access_notes: "",
  login_instructions: "",
  training_required: false,
  related_training_module: "",
  visible_to_agents: true,
};

export default function AdminSupplierAccessPage() {
  const { token } = useAuth();
  const suppliers = useApiResource("/supplier-access", {
    initialData: [],
    fallbackError: "We could not load supplier access records.",
  });
  const modules = useApiResource("/training/modules", {
    initialData: [],
    fallbackError: "We could not load training modules.",
  });
  const [form, setForm] = useState(blankSupplier);
  const [editingSupplierId, setEditingSupplierId] = useState(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const moduleById = useMemo(() => {
    const map = new Map();
    for (const module of modules.data || []) {
      map.set(Number(module.id), module);
    }
    return map;
  }, [modules.data]);

  function update(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function startEdit(supplier) {
    setEditingSupplierId(supplier.id);
    setMessage("");
    setError("");
    setForm({
      supplier_name: supplier.supplier_name || "",
      supplier_type: supplier.supplier_type || "Tour Operator",
      portal_url: supplier.portal_url || "",
      access_notes: supplier.access_notes || "",
      login_instructions: supplier.login_instructions || "",
      training_required: Boolean(supplier.training_required),
      related_training_module: supplier.related_training_module ? String(supplier.related_training_module) : "",
      visible_to_agents: Boolean(supplier.visible_to_agents),
    });
  }

  function resetForm() {
    setEditingSupplierId(null);
    setForm(blankSupplier);
  }

  async function saveSupplier(event) {
    event.preventDefault();
    setSaving(true);
    setMessage("");
    setError("");

    const relatedTrainingModule = form.related_training_module ? Number(form.related_training_module) : null;
    const payload = {
      supplier_name: form.supplier_name,
      supplier_type: form.supplier_type,
      portal_url: form.portal_url || null,
      access_notes: form.access_notes || null,
      login_instructions: form.login_instructions || null,
      training_required: Boolean(form.training_required || relatedTrainingModule),
      related_training_module: relatedTrainingModule,
      visible_to_agents: form.visible_to_agents,
    };

    try {
      if (editingSupplierId) {
        await apiClient.put(`/supplier-access/${editingSupplierId}`, payload, token);
        setMessage("Supplier access record updated.");
      } else {
        await apiClient.post("/supplier-access", payload, token);
        setMessage("Supplier access record created.");
      }
      resetForm();
      await suppliers.reload();
    } catch (err) {
      setError(getFriendlyError(err, "Supplier access could not be saved."));
    } finally {
      setSaving(false);
    }
  }

  if (suppliers.loading || modules.loading) {
    return (
      <AdminPageShell title="Supplier Access Admin" description="Loading supplier access records.">
        <LoadingState message="Loading supplier access..." />
      </AdminPageShell>
    );
  }

  return (
    <AdminPageShell title="Supplier Access Admin" description="Add and edit supplier access instructions for approved agents.">
      <div className="space-y-6">
        <ErrorBanner message={suppliers.error || modules.error || error} />
        {message ? <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm font-medium text-emerald-700">{message}</div> : null}

        <Card title={editingSupplierId ? "Edit Supplier Access" : "Add Supplier Access"} description="These details appear in the agent Supplier Access area after final approval.">
          <form onSubmit={saveSupplier} className="grid gap-4 lg:grid-cols-2">
            <FormField label="Supplier name">
              <TextInput required value={form.supplier_name} onChange={(event) => update("supplier_name", event.target.value)} placeholder="Example Supplier" />
            </FormField>
            <FormField label="Supplier type">
              <SelectInput value={form.supplier_type} onChange={(event) => update("supplier_type", event.target.value)}>
                {supplierTypes.map((type) => <option key={type} value={type}>{type}</option>)}
              </SelectInput>
            </FormField>
            <FormField label="Portal link">
              <TextInput value={form.portal_url} onChange={(event) => update("portal_url", event.target.value)} placeholder="https://..." />
            </FormField>
            <FormField label="Required training">
              <SelectInput value={form.related_training_module} onChange={(event) => update("related_training_module", event.target.value)}>
                <option value="">No specific training required</option>
                {(modules.data || []).map((module) => (
                  <option key={module.id} value={module.id}>
                    {module.title} ({module.training_track})
                  </option>
                ))}
              </SelectInput>
            </FormField>
            <div className="lg:col-span-2">
              <FormField label="How to access">
                <TextArea value={form.access_notes} onChange={(event) => update("access_notes", event.target.value)} placeholder="Explain where the agent goes and what they should do first." />
              </FormField>
            </div>
            <div className="lg:col-span-2">
              <FormField label="How to get a login">
                <TextArea value={form.login_instructions} onChange={(event) => update("login_instructions", event.target.value)} placeholder="Explain who to contact, what details are needed, or whether admin must request the login." />
              </FormField>
            </div>
            <div className="flex flex-wrap items-center gap-5 lg:col-span-2">
              <Checkbox label="Show to approved agents" checked={form.visible_to_agents} onChange={(value) => update("visible_to_agents", value)} />
              <Checkbox label="Training required" checked={form.training_required} onChange={(value) => update("training_required", value)} />
            </div>
            <div className="flex flex-wrap gap-3 lg:col-span-2">
              <PrimaryButton type="submit" icon={Plus} disabled={saving}>
                {saving ? "Saving..." : editingSupplierId ? "Save supplier" : "Add supplier"}
              </PrimaryButton>
              {editingSupplierId ? (
                <SecondaryButton type="button" icon={X} onClick={resetForm}>
                  Cancel edit
                </SecondaryButton>
              ) : null}
            </div>
          </form>
        </Card>

        <Card title="Supplier Access Records">
          <DataTable
            rows={suppliers.data || []}
            emptyMessage="No supplier access records have been created yet."
            columns={[
              { key: "supplier_name", label: "Supplier" },
              { key: "supplier_type", label: "Type" },
              {
                key: "training",
                label: "Required training",
                render: (row) => {
                  const module = row.related_training_module ? moduleById.get(Number(row.related_training_module)) : null;
                  return module ? `${module.title} (${module.training_track})` : row.training_required ? "Training required" : "None";
                },
              },
              { key: "visible_to_agents", label: "Visible", render: (row) => <StatusBadge status={row.visible_to_agents ? "Visible" : "Hidden"} /> },
              {
                key: "actions",
                label: "Actions",
                render: (row) => (
                  <button type="button" className="inline-flex items-center gap-1 font-semibold text-sky-700 hover:text-sky-900" onClick={() => startEdit(row)}>
                    <Pencil className="h-4 w-4" aria-hidden="true" />
                    Edit
                  </button>
                ),
              },
            ]}
          />
        </Card>
      </div>
    </AdminPageShell>
  );
}

function Checkbox({ label, checked, onChange }) {
  return (
    <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
      <input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} />
      {label}
    </label>
  );
}
