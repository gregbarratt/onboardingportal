import { FileText, FileVideo, Plus, Save, Trash2, Upload } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import {
  Card,
  ErrorBanner,
  FormField,
  LoadingState,
  PrimaryButton,
  SecondaryButton,
  SelectInput,
  TextArea,
  TextInput,
} from "../../components/ui.jsx";
import { apiClient } from "../../api/client.js";
import { useAuth } from "../../context/AuthContext.jsx";
import { getFriendlyError, useApiResource } from "../../hooks/useAgentPortalData.js";
import { trainingPublishedStatuses, trainingTracks } from "./adminConstants.js";
import AdminPageShell, { AdminLinkButton } from "./AdminPageShell.jsx";

const blankModule = {
  title: "",
  description: "",
  category_id: "",
  level: "Beginner",
  mandatory: false,
  estimated_completion_time: "30 minutes",
  content_type: "Text",
  content_url: "",
  video_url: "",
  pdf_url: "",
  text_content: "",
  quiz_required: false,
  pass_mark: "80",
  certificate_issued: false,
  renewal_required: false,
  renewal_period_months: "",
  expiry_date: "",
  training_track: "Onboarding",
  published_status: "Draft",
};

export default function AdminTrainingModuleBuilderPage() {
  const { moduleId } = useParams();
  const navigate = useNavigate();
  const { token } = useAuth();
  const existingModule = useApiResource(moduleId ? `/training/modules/${moduleId}` : "", {
    enabled: Boolean(moduleId),
    fallbackError: "We could not load this training module.",
  });
  const categories = useApiResource("/training/categories", {
    initialData: [],
    fallbackError: "We could not load training categories.",
  });
  const quiz = useApiResource(moduleId ? `/training/modules/${moduleId}/quiz` : "", {
    enabled: Boolean(moduleId),
    initialData: { questions: [] },
    fallbackError: "We could not load this quiz.",
  });
  const [form, setForm] = useState(blankModule);
  const [quizQuestions, setQuizQuestions] = useState([]);
  const [newCategory, setNewCategory] = useState("");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (categories.data?.length && !form.category_id) {
      setForm((current) => ({ ...current, category_id: String(categories.data[0].id) }));
    }
  }, [categories.data, form.category_id]);

  useEffect(() => {
    if (existingModule.data) {
      setForm({
        title: existingModule.data.title || "",
        description: existingModule.data.description || "",
        category_id: String(existingModule.data.category_id || ""),
        level: existingModule.data.level || "Beginner",
        mandatory: Boolean(existingModule.data.mandatory),
        estimated_completion_time: existingModule.data.estimated_completion_time || "30 minutes",
        content_type: existingModule.data.content_type || "Text",
        content_url: existingModule.data.content_url || "",
        video_url: existingModule.data.video_url || "",
        pdf_url: existingModule.data.pdf_url || "",
        text_content: existingModule.data.text_content || "",
        quiz_required: Boolean(existingModule.data.quiz_required),
        pass_mark: existingModule.data.pass_mark ?? "80",
        certificate_issued: Boolean(existingModule.data.certificate_issued),
        renewal_required: Boolean(existingModule.data.renewal_required),
        renewal_period_months: existingModule.data.renewal_period_months ?? "",
        expiry_date: existingModule.data.expiry_date || "",
        training_track: existingModule.data.training_track || "Onboarding",
        published_status: existingModule.data.published_status || "Draft",
      });
    }
  }, [existingModule.data]);

  useEffect(() => {
    if (quiz.data?.questions) {
      setQuizQuestions(
        quiz.data.questions.map((question) => ({
          clientId: `question-${question.id}`,
          id: question.id,
          question_text: question.question_text,
          options: question.options.map((option) => ({
            clientId: `option-${option.id}`,
            id: option.id,
            option_text: option.option_text,
            is_correct: Boolean(option.is_correct),
          })),
        })),
      );
    }
  }, [quiz.data]);

  function update(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function createCategory(event) {
    event.preventDefault();
    if (!newCategory.trim()) return;

    setError("");
    setMessage("");
    try {
      const category = await apiClient.post("/training/categories", { name: newCategory }, token);
      setNewCategory("");
      await categories.reload();
      update("category_id", String(category.id));
      setMessage("Category added.");
    } catch (err) {
      setError(getFriendlyError(err, "We could not add this category."));
    }
  }

  async function saveModule(event) {
    event.preventDefault();
    setSaving(true);
    setMessage("");
    setError("");

    const payload = {
      ...form,
      category_id: Number(form.category_id),
      pass_mark: form.pass_mark === "" ? null : Number(form.pass_mark),
      renewal_period_months: form.renewal_period_months === "" ? null : Number(form.renewal_period_months),
      expiry_date: form.expiry_date || null,
      quiz_required: Boolean(form.quiz_required || quizQuestions.length),
    };

    try {
      const savedModule = moduleId
        ? await apiClient.put(`/training/modules/${moduleId}`, payload, token)
        : await apiClient.post("/training/modules", payload, token);

      await apiClient.put(
        `/training/modules/${savedModule.id}/quiz`,
        {
          questions: quizQuestions.map((question) => ({
            id: question.id || null,
            question_text: question.question_text,
            options: question.options.map((option) => ({
              id: option.id || null,
              option_text: option.option_text,
              is_correct: Boolean(option.is_correct),
            })),
          })),
        },
        token,
      );

      setMessage("Training module saved.");
      if (!moduleId) {
        navigate(`/admin/training/${savedModule.id}/edit`);
      }
    } catch (err) {
      setError(getFriendlyError(err, "We could not save this training module."));
    } finally {
      setSaving(false);
    }
  }

  async function uploadMaterial(materialType, file) {
    if (!moduleId) {
      setError("Save the module before uploading files.");
      return;
    }
    if (!file) {
      setError("Choose a file first.");
      return;
    }

    setError("");
    setMessage("");
    try {
      const fileContentBase64 = await readFileAsBase64(file);
      const updatedModule = await apiClient.post(
        `/training/modules/${moduleId}/materials`,
        {
          material_type: materialType,
          file_name: file.name,
          file_content_base64: fileContentBase64,
        },
        token,
      );
      setForm((current) => ({
        ...current,
        content_type: updatedModule.content_type || current.content_type,
        video_url: updatedModule.video_url || current.video_url,
        pdf_url: updatedModule.pdf_url || current.pdf_url,
      }));
      setMessage(`${materialType} uploaded and embedded in this lesson.`);
    } catch (err) {
      setError(getFriendlyError(err, `We could not upload this ${materialType.toLowerCase()} file.`));
    }
  }

  function addQuestion() {
    const id = crypto.randomUUID();
    setQuizQuestions((current) => [
      ...current,
      {
        clientId: id,
        question_text: "",
        options: [
          { clientId: `${id}-a`, option_text: "", is_correct: true },
          { clientId: `${id}-b`, option_text: "", is_correct: false },
        ],
      },
    ]);
    update("quiz_required", true);
  }

  function updateQuestion(questionId, value) {
    setQuizQuestions((current) =>
      current.map((question) => (question.clientId === questionId ? { ...question, question_text: value } : question)),
    );
  }

  function removeQuestion(questionId) {
    setQuizQuestions((current) => current.filter((question) => question.clientId !== questionId));
  }

  function addOption(questionId) {
    setQuizQuestions((current) =>
      current.map((question) =>
        question.clientId === questionId
          ? {
              ...question,
              options: [
                ...question.options,
                { clientId: crypto.randomUUID(), option_text: "", is_correct: false },
              ],
            }
          : question,
      ),
    );
  }

  function updateOption(questionId, optionId, value) {
    setQuizQuestions((current) =>
      current.map((question) =>
        question.clientId === questionId
          ? {
              ...question,
              options: question.options.map((option) =>
                option.clientId === optionId ? { ...option, option_text: value } : option,
              ),
            }
          : question,
      ),
    );
  }

  function setCorrectOption(questionId, optionId) {
    setQuizQuestions((current) =>
      current.map((question) =>
        question.clientId === questionId
          ? {
              ...question,
              options: question.options.map((option) => ({
                ...option,
                is_correct: option.clientId === optionId,
              })),
            }
          : question,
      ),
    );
  }

  function removeOption(questionId, optionId) {
    setQuizQuestions((current) =>
      current.map((question) =>
        question.clientId === questionId
          ? { ...question, options: question.options.filter((option) => option.clientId !== optionId) }
          : question,
      ),
    );
  }

  if (existingModule.loading || categories.loading || quiz.loading) {
    return (
      <AdminPageShell title="Training Module Builder" description="Loading training module.">
        <LoadingState message="Loading module builder..." />
      </AdminPageShell>
    );
  }

  return (
    <AdminPageShell
      title="Training Module Builder"
      description="Create lessons with embedded files, written content, and quizzes."
      actions={<AdminLinkButton to="/admin/training">Back to modules</AdminLinkButton>}
    >
      <div className="space-y-6">
        <ErrorBanner message={existingModule.error || categories.error || quiz.error || error} />
        {message ? <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm font-medium text-emerald-700">{message}</div> : null}

        <form onSubmit={saveModule} className="space-y-6">
          <Card title={moduleId ? "Edit Module" : "New Module"} description="This controls the lesson title, category, status, and written content.">
            <div className="grid gap-4 md:grid-cols-2">
              <FormField label="Title">
                <TextInput required value={form.title} onChange={(event) => update("title", event.target.value)} />
              </FormField>
              <FormField label="Category">
                <SelectInput required value={form.category_id} onChange={(event) => update("category_id", event.target.value)}>
                  {(categories.data || []).map((category) => (
                    <option key={category.id} value={category.id}>{category.name}</option>
                  ))}
                </SelectInput>
              </FormField>
              <FormField label="Level">
                <TextInput value={form.level} onChange={(event) => update("level", event.target.value)} />
              </FormField>
              <FormField label="Estimated completion time">
                <TextInput value={form.estimated_completion_time} onChange={(event) => update("estimated_completion_time", event.target.value)} />
              </FormField>
              <FormField label="Training track">
                <SelectInput value={form.training_track} onChange={(event) => update("training_track", event.target.value)}>
                  {trainingTracks.map((track) => <option key={track} value={track}>{track}</option>)}
                </SelectInput>
              </FormField>
              <FormField label="Published status">
                <SelectInput value={form.published_status} onChange={(event) => update("published_status", event.target.value)}>
                  {trainingPublishedStatuses.map((status) => <option key={status} value={status}>{status}</option>)}
                </SelectInput>
              </FormField>
              <FormField label="Content type">
                <SelectInput value={form.content_type} onChange={(event) => update("content_type", event.target.value)}>
                  <option value="Text">Text</option>
                  <option value="Video">Video</option>
                  <option value="PDF">PDF</option>
                  <option value="Mixed">Mixed</option>
                  <option value="Quiz">Quiz</option>
                </SelectInput>
              </FormField>
              <FormField label="Pass mark">
                <TextInput type="number" min="0" max="100" value={form.pass_mark} onChange={(event) => update("pass_mark", event.target.value)} />
              </FormField>
              <FormField label="Expiry date">
                <TextInput type="date" value={form.expiry_date} onChange={(event) => update("expiry_date", event.target.value)} />
              </FormField>
              <FormField label="Renewal period months">
                <TextInput type="number" min="1" value={form.renewal_period_months} onChange={(event) => update("renewal_period_months", event.target.value)} />
              </FormField>
              <div className="md:col-span-2">
                <FormField label="Description">
                  <TextArea value={form.description} onChange={(event) => update("description", event.target.value)} />
                </FormField>
              </div>
              <div className="md:col-span-2">
                <FormField label="Written lesson content">
                  <TextArea value={form.text_content} onChange={(event) => update("text_content", event.target.value)} className="min-h-48" />
                </FormField>
              </div>
              <div className="md:col-span-2 flex flex-wrap gap-5">
                <Checkbox label="Mandatory" checked={form.mandatory} onChange={(value) => update("mandatory", value)} />
                <Checkbox label="Quiz required" checked={form.quiz_required} onChange={(value) => update("quiz_required", value)} />
                <Checkbox label="Auto-generate certificate on completion" checked={form.certificate_issued} onChange={(value) => update("certificate_issued", value)} />
                <Checkbox label="Renewal required" checked={form.renewal_required} onChange={(value) => update("renewal_required", value)} />
              </div>
            </div>
          </Card>

          <Card title="Embedded Files" description="Upload the files here so agents can watch or read them inside the portal.">
            <div className="grid gap-4 lg:grid-cols-2">
              <MaterialUpload
                title="Video"
                icon={FileVideo}
                accept="video/mp4,video/webm,video/quicktime,.m4v"
                disabled={!moduleId}
                saved={Boolean(form.video_url)}
                onUpload={(file) => uploadMaterial("Video", file)}
              />
              <MaterialUpload
                title="PDF"
                icon={FileText}
                accept="application/pdf,.pdf"
                disabled={!moduleId}
                saved={Boolean(form.pdf_url)}
                onUpload={(file) => uploadMaterial("PDF", file)}
              />
            </div>
            {!moduleId ? <p className="mt-3 text-sm text-slate-500">Save the module once before uploading video or PDF files.</p> : null}
          </Card>

          <Card
            title="Quiz Builder"
            description="Create multiple-choice questions. The portal will score the agent and log every attempt."
            actions={<SecondaryButton type="button" icon={Plus} onClick={addQuestion}>Add question</SecondaryButton>}
          >
            <div className="space-y-4">
              {quizQuestions.length ? (
                quizQuestions.map((question, questionIndex) => (
                  <div key={question.clientId} className="rounded-lg border border-slate-200 p-4">
                    <div className="flex items-start justify-between gap-3">
                      <FormField label={`Question ${questionIndex + 1}`}>
                        <TextArea required value={question.question_text} onChange={(event) => updateQuestion(question.clientId, event.target.value)} />
                      </FormField>
                      <button type="button" className="mt-7 text-rose-700" onClick={() => removeQuestion(question.clientId)} aria-label="Remove question">
                        <Trash2 className="h-4 w-4" aria-hidden="true" />
                      </button>
                    </div>

                    <div className="mt-4 space-y-3">
                      {question.options.map((option, optionIndex) => (
                        <div key={option.clientId} className="grid gap-3 sm:grid-cols-[auto_1fr_auto] sm:items-center">
                          <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
                            <input
                              type="radio"
                              name={`correct-${question.clientId}`}
                              checked={option.is_correct}
                              onChange={() => setCorrectOption(question.clientId, option.clientId)}
                            />
                            Correct
                          </label>
                          <TextInput
                            required
                            placeholder={`Answer option ${optionIndex + 1}`}
                            value={option.option_text}
                            onChange={(event) => updateOption(question.clientId, option.clientId, event.target.value)}
                          />
                          <button type="button" className="text-rose-700" onClick={() => removeOption(question.clientId, option.clientId)} aria-label="Remove answer option">
                            <Trash2 className="h-4 w-4" aria-hidden="true" />
                          </button>
                        </div>
                      ))}
                    </div>

                    <div className="mt-3">
                      <SecondaryButton type="button" icon={Plus} onClick={() => addOption(question.clientId)}>Add answer option</SecondaryButton>
                    </div>
                  </div>
                ))
              ) : (
                <p className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-5 text-sm text-slate-600">
                  No quiz questions yet. Add questions if this module needs a pass or fail result.
                </p>
              )}
            </div>
          </Card>

          <PrimaryButton type="submit" icon={Save} disabled={saving}>
            {saving ? "Saving..." : "Save module"}
          </PrimaryButton>
        </form>

        <Card title="Categories" description="Add a new training category if the list above does not have the one you need.">
          <form onSubmit={createCategory} className="grid gap-3 sm:grid-cols-[1fr_auto]">
            <TextInput value={newCategory} onChange={(event) => setNewCategory(event.target.value)} placeholder="New category name" />
            <SecondaryButton type="submit" icon={Plus}>Add category</SecondaryButton>
          </form>
        </Card>
      </div>
    </AdminPageShell>
  );
}

function MaterialUpload({ title, icon: Icon, accept, disabled, saved, onUpload }) {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);

  async function handleUpload() {
    setUploading(true);
    try {
      await onUpload(file);
      setFile(null);
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="rounded-lg border border-slate-200 p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Icon className="h-5 w-5 text-sky-700" aria-hidden="true" />
          <h3 className="font-semibold text-slate-950">{title}</h3>
        </div>
        {saved ? <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700 ring-1 ring-emerald-200">Uploaded</span> : null}
      </div>
      <input
        type="file"
        accept={accept}
        disabled={disabled}
        onChange={(event) => setFile(event.target.files?.[0] || null)}
        className="block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 shadow-sm file:mr-4 file:rounded-md file:border-0 file:bg-sky-50 file:px-3 file:py-1.5 file:text-sm file:font-semibold file:text-sky-700 hover:file:bg-sky-100 disabled:cursor-not-allowed disabled:bg-slate-50"
      />
      <div className="mt-3">
        <SecondaryButton type="button" icon={Upload} disabled={disabled || uploading || !file} onClick={handleUpload}>
          {uploading ? "Uploading..." : `Upload ${title}`}
        </SecondaryButton>
      </div>
    </div>
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

function readFileAsBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = String(reader.result || "");
      resolve(result.split(",", 2)[1] || result);
    };
    reader.onerror = () => reject(new Error("The file could not be read."));
    reader.readAsDataURL(file);
  });
}
