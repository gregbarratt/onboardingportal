import { ArrowLeft, CheckCircle2, ExternalLink, FileText, FileVideo, Send } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { apiClient } from "../../api/client.js";
import { useAuth } from "../../context/AuthContext.jsx";
import { Card, ErrorBanner, LoadingState, PageHeader, PrimaryButton, ProgressBar, StatusBadge } from "../../components/ui.jsx";
import {
  getFriendlyError,
  useAgentProfile,
  useAgentResource,
  useApiResource,
} from "../../hooks/useAgentPortalData.js";
import { formatDateTime, percentage } from "../../utils/formatters.js";

export default function TrainingModuleDetailPage() {
  const { moduleId } = useParams();
  const { token } = useAuth();
  const { profile, loading: profileLoading, error: profileError } = useAgentProfile();
  const module = useApiResource(`/training/modules/${moduleId}`, {
    fallbackError: "We could not load this training module.",
  });
  const quiz = useApiResource(`/training/modules/${moduleId}/quiz`, {
    initialData: { questions: [] },
    fallbackError: "We could not load this module quiz.",
  });
  const attempts = useApiResource(`/training/modules/${moduleId}/quiz/attempts`, {
    initialData: [],
    fallbackError: "We could not load your quiz attempts.",
  });
  const progress = useAgentResource(profile, (agentId) => `/agents/${agentId}/training`, {
    initialData: [],
  });
  const [selectedAnswers, setSelectedAnswers] = useState({});
  const [submittingQuiz, setSubmittingQuiz] = useState(false);
  const [markingComplete, setMarkingComplete] = useState(false);
  const [actionMessage, setActionMessage] = useState("");
  const [actionError, setActionError] = useState("");

  const data = module.data;
  const quizQuestions = useMemo(() => quiz.data?.questions || [], [quiz.data]);
  const progressRow = useMemo(
    () => (progress.data || []).find((item) => Number(item.training_module_id) === Number(moduleId)),
    [moduleId, progress.data],
  );
  const latestAttempt = (attempts.data || [])[0];
  const completedQuestionCount = quizQuestions.filter((question) => selectedAnswers[question.id]).length;

  useEffect(() => {
    setSelectedAnswers({});
    setActionMessage("");
    setActionError("");
  }, [moduleId]);

  async function submitQuiz(event) {
    event.preventDefault();
    setActionError("");
    setActionMessage("");

    if (completedQuestionCount !== quizQuestions.length) {
      setActionError("Please answer every quiz question before submitting.");
      return;
    }

    setSubmittingQuiz(true);
    try {
      const result = await apiClient.post(
        `/training/modules/${moduleId}/quiz/attempts`,
        {
          answers: quizQuestions.map((question) => ({
            question_id: question.id,
            selected_option_id: Number(selectedAnswers[question.id]),
          })),
        },
        token,
      );
      await Promise.all([attempts.reload(), progress.reload()]);
      setActionMessage(result.passed ? `Passed with ${result.score}%.` : `Failed with ${result.score}%. You can try again.`);
    } catch (err) {
      setActionError(getFriendlyError(err, "We could not submit this quiz."));
    } finally {
      setSubmittingQuiz(false);
    }
  }

  async function markLessonComplete() {
    if (!profile?.id || !progressRow?.id) {
      setActionError("Your training record is still loading. Please try again in a moment.");
      return;
    }

    setActionError("");
    setActionMessage("");
    setMarkingComplete(true);
    try {
      await apiClient.put(
        `/agents/${profile.id}/training/${progressRow.id}`,
        { progress_status: "Complete" },
        token,
      );
      await progress.reload();
      setActionMessage("Lesson marked as complete.");
    } catch (err) {
      setActionError(getFriendlyError(err, "We could not mark this lesson as complete."));
    } finally {
      setMarkingComplete(false);
    }
  }

  if (module.loading || quiz.loading || profileLoading || progress.loading || attempts.loading) {
    return (
      <div className="space-y-6">
        <PageHeader title="Training Module" description="Loading the lesson content." />
        <LoadingState message="Loading training module..." />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Training Academy"
        title={data?.title || "Training Module"}
        description={data?.description || "View this training lesson and any attached resources."}
        actions={
          <Link className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50" to="/training">
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
            Back to training
          </Link>
        }
      />

      <ErrorBanner message={module.error || quiz.error || attempts.error || progress.error || profileError || actionError} />
      {actionMessage ? <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm font-medium text-emerald-700">{actionMessage}</div> : null}

      {data ? (
        <>
          <div className="grid gap-4 md:grid-cols-4">
            <Card title="Category">
              <p className="text-sm font-medium text-slate-900">{getCategoryName(data.category)}</p>
            </Card>
            <Card title="Level">
              <p className="text-sm font-medium text-slate-900">{data.level || "Not set"}</p>
            </Card>
            <Card title="Status">
              <StatusBadge status={data.published_status} />
            </Card>
            <Card title="Quiz">
              <p className="text-sm font-medium text-slate-900">{data.quiz_required ? `Required, pass mark ${data.pass_mark || 0}%` : "Not required"}</p>
            </Card>
            <Card title="Your progress">
              <StatusBadge status={progressRow?.progress_status || "Not Started"} />
            </Card>
          </div>

          <TrainingMediaCard data={data} />

          <Card title="Lesson Content">
            {data.text_content ? (
              <div className="whitespace-pre-wrap text-sm leading-6 text-slate-700">{data.text_content}</div>
            ) : (
              <p className="text-sm text-slate-600">No written content has been added yet.</p>
            )}
          </Card>

          <QuizCard
            data={data}
            questions={quizQuestions}
            latestAttempt={latestAttempt}
            selectedAnswers={selectedAnswers}
            completedQuestionCount={completedQuestionCount}
            progressRow={progressRow}
            submittingQuiz={submittingQuiz}
            markingComplete={markingComplete}
            onSelectAnswer={(questionId, optionId) =>
              setSelectedAnswers((current) => ({ ...current, [questionId]: optionId }))
            }
            onSubmitQuiz={submitQuiz}
            onMarkComplete={markLessonComplete}
          />

          {data.content_url ? (
            <Card title="Additional Resource">
              <ResourceLink label="Open resource" url={data.content_url} />
            </Card>
          ) : null}
        </>
      ) : null}
    </div>
  );
}

function getCategoryName(category) {
  if (!category) return "Training";
  if (typeof category === "string") return category;
  return category.name || "Training";
}

function TrainingMediaCard({ data }) {
  const hasVideo = Boolean(data.video_url);
  const hasPdf = Boolean(data.pdf_url);

  if (!hasVideo && !hasPdf) {
    return null;
  }

  return (
    <Card title="Embedded Training Files" description="These files play or open inside the portal.">
      <div className="grid gap-5 xl:grid-cols-2">
        {hasVideo ? (
          <div>
            <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-slate-900">
              <FileVideo className="h-4 w-4 text-sky-700" aria-hidden="true" />
              Video lesson
            </div>
            <video
              controls
              controlsList="nodownload noplaybackrate"
              disablePictureInPicture
              onContextMenu={(event) => event.preventDefault()}
              src={data.video_url}
              className="aspect-video w-full rounded-lg border border-slate-200 bg-slate-950"
            />
          </div>
        ) : null}

        {hasPdf ? (
          <div>
            <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-slate-900">
              <FileText className="h-4 w-4 text-sky-700" aria-hidden="true" />
              PDF lesson
            </div>
            <iframe
              title={`${data.title} PDF`}
              src={buildProtectedPdfViewUrl(data.pdf_url)}
              sandbox="allow-same-origin allow-scripts"
              className="h-[520px] w-full rounded-lg border border-slate-200 bg-white"
            />
            <p className="mt-2 text-xs text-slate-500">
              This document is shown inside the portal. Download controls are hidden where the browser allows it.
            </p>
          </div>
        ) : null}
      </div>
    </Card>
  );
}

function buildProtectedPdfViewUrl(url) {
  if (!url) return "";
  const separator = url.includes("#") ? "&" : "#";
  return `${url}${separator}toolbar=0&navpanes=0&scrollbar=0&view=FitH`;
}

function QuizCard({
  data,
  questions,
  latestAttempt,
  selectedAnswers,
  completedQuestionCount,
  progressRow,
  submittingQuiz,
  markingComplete,
  onSelectAnswer,
  onSubmitQuiz,
  onMarkComplete,
}) {
  const needsQuiz = data.quiz_required || questions.length > 0;
  const quizProgress = percentage(completedQuestionCount, questions.length);

  if (!needsQuiz) {
    return (
      <Card
        title="Completion"
        description="This lesson does not need a quiz. Agents can mark it complete after reading or watching the content."
        actions={
          progressRow?.progress_status === "Complete" ? null : (
            <PrimaryButton type="button" icon={CheckCircle2} disabled={markingComplete} onClick={onMarkComplete}>
              {markingComplete ? "Saving..." : "Mark lesson complete"}
            </PrimaryButton>
          )
        }
      >
        <StatusBadge status={progressRow?.progress_status || "Not Started"} />
      </Card>
    );
  }

  return (
    <Card title="Quiz" description="Submit your answers to receive a pass or fail result. Failed quizzes can be taken again.">
      {latestAttempt ? (
        <div className="mb-4 grid gap-3 rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm md:grid-cols-3">
          <div>
            <p className="font-medium text-slate-500">Latest result</p>
            <div className="mt-1">
              <StatusBadge status={latestAttempt.status} />
            </div>
          </div>
          <div>
            <p className="font-medium text-slate-500">Score</p>
            <p className="mt-1 text-lg font-semibold text-slate-950">{latestAttempt.score}%</p>
          </div>
          <div>
            <p className="font-medium text-slate-500">Submitted</p>
            <p className="mt-1 font-semibold text-slate-900">{formatDateTime(latestAttempt.submitted_at)}</p>
          </div>
          {latestAttempt.status === "Redo Requested" ? (
            <p className="md:col-span-3 text-amber-700">
              Admin has asked for this quiz to be completed again. {latestAttempt.admin_notes || ""}
            </p>
          ) : null}
        </div>
      ) : null}

      {questions.length ? (
        <form onSubmit={onSubmitQuiz} className="space-y-5">
          <ProgressBar value={quizProgress} label={`${completedQuestionCount} of ${questions.length} questions answered`} />
          {questions.map((question, index) => (
            <fieldset key={question.id} className="rounded-lg border border-slate-200 p-4">
              <legend className="px-1 text-sm font-semibold text-slate-950">
                Question {index + 1}: {question.question_text}
              </legend>
              <div className="mt-3 space-y-2">
                {question.options.map((option) => (
                  <label key={option.id} className="flex cursor-pointer items-start gap-3 rounded-lg border border-slate-200 p-3 text-sm text-slate-700 hover:bg-sky-50">
                    <input
                      type="radio"
                      name={`question-${question.id}`}
                      value={option.id}
                      checked={Number(selectedAnswers[question.id]) === Number(option.id)}
                      onChange={() => onSelectAnswer(question.id, option.id)}
                      className="mt-0.5"
                    />
                    <span>{option.option_text}</span>
                  </label>
                ))}
              </div>
            </fieldset>
          ))}
          <PrimaryButton type="submit" icon={Send} disabled={submittingQuiz}>
            {submittingQuiz ? "Submitting..." : "Submit quiz"}
          </PrimaryButton>
        </form>
      ) : (
        <p className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-5 text-sm text-slate-600">
          This module says a quiz is required, but admin has not added the questions yet.
        </p>
      )}
    </Card>
  );
}

function ResourceLink({ label, url }) {
  if (!url) {
    return <div className="rounded-lg border border-slate-200 p-4 text-sm text-slate-500">{label}: Not added</div>;
  }

  return (
    <a href={url} target="_blank" rel="noreferrer" className="flex items-center justify-between gap-3 rounded-lg border border-slate-200 p-4 text-sm font-semibold text-sky-700 hover:bg-sky-50">
      {label}
      <ExternalLink className="h-4 w-4" aria-hidden="true" />
    </a>
  );
}
