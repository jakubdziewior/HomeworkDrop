"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import { ApiSubmission, ApiTask, apiRequest } from "@/lib/api";
import {
  PlusCircle,
  Users,
  CheckCircle2,
  Clock,
  Calendar,
  FileText,
  Award,
  Filter,
  Lock,
  Download,
  Trash2,
  Pencil,
  AlertCircle,
  RefreshCw,
} from "lucide-react";

function formatDateTime(isoString: string): string {
  return new Date(isoString).toLocaleString("pl-PL", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function toLocalDateTimeInput(isoString: string): string {
  const d = new Date(isoString);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(
    d.getHours()
  )}:${pad(d.getMinutes())}`;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

export default function TeacherDashboard() {
  const { user, isLoading } = useAuth();
  const [tasks, setTasks] = useState<ApiTask[]>([]);
  const [submissions, setSubmissions] = useState<ApiSubmission[]>([]);
  const [dataLoading, setDataLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [selectedTaskId, setSelectedTaskId] = useState<number | "all">("all");
  const [showTaskModal, setShowTaskModal] = useState(false);
  const [editingTaskId, setEditingTaskId] = useState<number | null>(null);

  const [taskTitle, setTaskTitle] = useState("");
  const [taskDescription, setTaskDescription] = useState("");
  const [taskDeadline, setTaskDeadline] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [taskSubmitting, setTaskSubmitting] = useState(false);

  const [confirmDeleteTaskId, setConfirmDeleteTaskId] = useState<number | null>(null);

  const [activeGradingSubId, setActiveGradingSubId] = useState<number | null>(null);
  const [gradeInput, setGradeInput] = useState<number>(5.0);
  const [feedbackInput, setFeedbackInput] = useState<string>("");
  const [gradeError, setGradeError] = useState<string | null>(null);
  const [gradeSubmitting, setGradeSubmitting] = useState(false);

  const loadData = useCallback(async () => {
    if (!user || user.role !== "teacher") return;
    setDataLoading(true);
    setLoadError(null);
    try {
      const allTasks = await apiRequest<ApiTask[]>(
        "/api/v1/tasks",
        {},
        "Nie udało się pobrać listy zadań."
      );
      const ownTasks = allTasks.filter((t) => t.created_by === user.id);
      setTasks(ownTasks);

      const perTask = await Promise.all(
        ownTasks.map((t) =>
          apiRequest<ApiSubmission[]>(
            `/api/v1/tasks/${t.id}/submissions`,
            {},
            "Nie udało się pobrać zgłoszeń."
          )
        )
      );
      setSubmissions(perTask.flat());
    } catch (err: unknown) {
      setLoadError(err instanceof Error ? err.message : "Błąd pobierania danych.");
    } finally {
      setDataLoading(false);
    }
  }, [user]);

  useEffect(() => {
    if (!isLoading && user?.role === "teacher") {
      loadData();
    }
  }, [isLoading, user, loadData]);

  if (isLoading) {
    return (
      <div className="max-w-md mx-auto my-16 p-8 text-center text-xs text-slate-400">
        Ładowanie panelu prowadzącego...
      </div>
    );
  }

  if (!user) {
    return (
      <div className="max-w-md mx-auto my-16 p-8 bg-slate-900 border border-slate-800 rounded-2xl text-center space-y-4 shadow-xl">
        <div className="w-12 h-12 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400 mx-auto">
          <Lock className="w-6 h-6" />
        </div>
        <h2 className="text-xl font-bold text-white">Wymagane logowanie</h2>
        <p className="text-xs text-slate-400">
          Dostęp do panelu prowadzącego wymaga zalogowania na konto z uprawnieniami prowadzącego.
        </p>
        <Link
          href="/login?mode=login"
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs transition-colors shadow-sm"
        >
          Przejdź do logowania
        </Link>
      </div>
    );
  }

  if (user.role === "student") {
    return (
      <div className="max-w-md mx-auto my-16 p-8 bg-slate-900 border border-slate-800 rounded-2xl text-center space-y-4 shadow-xl">
        <h2 className="text-xl font-bold text-white">Brak uprawnień</h2>
        <p className="text-xs text-slate-400">
          Jesteś zalogowany jako Student. Panel jest dostępny wyłącznie dla Prowadzących.
        </p>
        <Link
          href="/student"
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs transition-colors shadow-sm"
        >
          Przejdź do Panelu Studenta
        </Link>
      </div>
    );
  }

  const openCreateModal = () => {
    setEditingTaskId(null);
    setTaskTitle("");
    setTaskDescription("");
    setTaskDeadline("");
    setFormError(null);
    setShowTaskModal(true);
  };

  const openEditModal = (task: ApiTask) => {
    setEditingTaskId(task.id);
    setTaskTitle(task.title);
    setTaskDescription(task.description);
    setTaskDeadline(toLocalDateTimeInput(task.deadline));
    setFormError(null);
    setShowTaskModal(true);
  };

  const handleSaveTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (taskTitle.trim().length < 3) {
      setFormError("Tytuł musi zawierać co najmniej 3 znaki.");
      return;
    }
    if (!taskDeadline.trim()) {
      setFormError("Termin oddania jest wymagany.");
      return;
    }

    const parsedDeadline = new Date(taskDeadline);
    if (Number.isNaN(parsedDeadline.getTime())) {
      setFormError("Nieprawidłowy format daty.");
      return;
    }

    setTaskSubmitting(true);
    setFormError(null);

    try {
      const payload = {
        title: taskTitle.trim(),
        description: taskDescription.trim(),
        deadline: parsedDeadline.toISOString(),
      };

      if (editingTaskId !== null) {
        const updated = await apiRequest<ApiTask>(
          `/api/v1/tasks/${editingTaskId}`,
          {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
          },
          "Nie udało się zaktualizować zadania."
        );
        setTasks((prev) => prev.map((t) => (t.id === updated.id ? updated : t)));
      } else {
        const created = await apiRequest<ApiTask>(
          "/api/v1/tasks",
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
          },
          "Nie udało się utworzyć zadania."
        );
        setTasks((prev) => [created, ...prev]);
      }

      setShowTaskModal(false);
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : "Błąd zapisu zadania.");
    } finally {
      setTaskSubmitting(false);
    }
  };

  const handleDeleteTask = async (taskId: number) => {
    try {
      await apiRequest<void>(
        `/api/v1/tasks/${taskId}`,
        { method: "DELETE" },
        "Nie udało się usunąć zadania."
      );
      setTasks((prev) => prev.filter((t) => t.id !== taskId));
      setSubmissions((prev) => prev.filter((s) => s.task_id !== taskId));
      if (selectedTaskId === taskId) {
        setSelectedTaskId("all");
      }
      setConfirmDeleteTaskId(null);
    } catch (err: unknown) {
      setLoadError(err instanceof Error ? err.message : "Błąd usuwania zadania.");
    }
  };

  const handleSaveGrade = async (submissionId: number) => {
    setGradeSubmitting(true);
    setGradeError(null);
    try {
      const updated = await apiRequest<ApiSubmission>(
        `/api/v1/submissions/${submissionId}/grade`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            grade: gradeInput,
            feedback: feedbackInput.trim(),
          }),
        },
        "Nie udało się zapisać oceny."
      );
      setSubmissions((prev) =>
        prev.map((sub) => (sub.id === updated.id ? updated : sub))
      );
      setActiveGradingSubId(null);
      setFeedbackInput("");
    } catch (err: unknown) {
      setGradeError(err instanceof Error ? err.message : "Błąd zapisu oceny.");
    } finally {
      setGradeSubmitting(false);
    }
  };

  const filteredSubmissions =
    selectedTaskId === "all"
      ? submissions
      : submissions.filter((s) => s.task_id === selectedTaskId);

  return (
    <div className="space-y-8">
      <header className="border-b border-slate-800 pb-4 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-100">
            Panel Prowadzącego
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Zarządzanie zadaniami i ocenianie przesłanych prac studentów.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={loadData}
            disabled={dataLoading}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-slate-800 text-xs text-slate-300 hover:text-white hover:border-slate-700 disabled:opacity-50 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${dataLoading ? "animate-spin" : ""}`} />
            Odśwież
          </button>

          <button
            onClick={openCreateModal}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs transition-colors shadow-sm"
          >
            <PlusCircle className="w-4 h-4" />
            Utwórz nowe zadanie
          </button>
        </div>
      </header>

      {loadError && (
        <div className="p-3 bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs rounded-xl flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{loadError}</span>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-4 bg-slate-900 border border-slate-800 rounded-xl">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium uppercase">
            <span>Twoje zadania</span>
            <FileText className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-2xl font-bold text-slate-100 mt-2">
            {tasks.length}
          </div>
        </div>

        <div className="p-4 bg-slate-900 border border-slate-800 rounded-xl">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium uppercase">
            <span>Nadesłane prace</span>
            <Users className="w-4 h-4 text-blue-400" />
          </div>
          <div className="text-2xl font-bold text-slate-100 mt-2">
            {submissions.length}
          </div>
        </div>

        <div className="p-4 bg-slate-900 border border-slate-800 rounded-xl">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium uppercase">
            <span>Ocenione</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-slate-100 mt-2">
            {submissions.filter((s) => s.status === "graded").length} /{" "}
            {submissions.length}
          </div>
        </div>
      </div>

      <div className="space-y-3">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          Lista zadań ({tasks.length})
        </h3>

        {tasks.length === 0 ? (
          <div className="p-6 bg-slate-900/40 border border-slate-800 rounded-xl text-center text-xs text-slate-500">
            Nie utworzono jeszcze żadnych zadań. Kliknij &bdquo;Utwórz nowe zadanie&rdquo;, aby dodać pierwszy temat.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {tasks.map((task) => {
              const expired =
                task.is_expired || new Date(task.deadline).getTime() <= Date.now();
              const subCount = submissions.filter((s) => s.task_id === task.id).length;
              const confirmingDelete = confirmDeleteTaskId === task.id;

              return (
                <div
                  key={task.id}
                  className="p-4 bg-slate-900/60 border border-slate-800/80 rounded-xl flex flex-col justify-between gap-3"
                >
                  <div className="space-y-1.5">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-2 min-w-0">
                        <span className="text-xs font-mono text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded shrink-0">
                          #{task.id}
                        </span>
                        <h4 className="font-semibold text-sm text-slate-100 truncate">
                          {task.title}
                        </h4>
                      </div>
                      <span
                        className={`shrink-0 px-2 py-0.5 rounded-full text-[11px] font-medium border ${
                          expired
                            ? "bg-rose-500/10 text-rose-400 border-rose-500/20"
                            : "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                        }`}
                      >
                        {expired ? "Po terminie" : "Aktywne"}
                      </span>
                    </div>
                    <p className="text-xs text-slate-400 line-clamp-2">
                      {task.description || "Brak opisu."}
                    </p>
                  </div>

                  <div className="pt-2 border-t border-slate-800/60 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-400">
                    <div className="flex items-center gap-3">
                      <span className="inline-flex items-center gap-1">
                        <Calendar className="w-3.5 h-3.5 text-slate-500" />
                        {formatDateTime(task.deadline)}
                      </span>
                      <span>Zgłoszenia: {subCount}</span>
                    </div>

                    <div className="flex items-center gap-1.5">
                      <button
                        type="button"
                        onClick={() => openEditModal(task)}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-200 text-[11px] transition-colors"
                      >
                        <Pencil className="w-3 h-3" />
                        Edytuj
                      </button>

                      {confirmingDelete ? (
                        <div className="inline-flex items-center gap-1">
                          <button
                            type="button"
                            onClick={() => handleDeleteTask(task.id)}
                            className="px-2.5 py-1 rounded-md bg-rose-600 hover:bg-rose-500 text-white text-[11px] font-medium"
                          >
                            Potwierdź
                          </button>
                          <button
                            type="button"
                            onClick={() => setConfirmDeleteTaskId(null)}
                            className="px-2 py-1 rounded-md border border-slate-700 text-slate-400 text-[11px]"
                          >
                            Anuluj
                          </button>
                        </div>
                      ) : (
                        <button
                          type="button"
                          onClick={() => setConfirmDeleteTaskId(task.id)}
                          className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/20 text-[11px] transition-colors"
                        >
                          <Trash2 className="w-3 h-3" />
                          Usuń
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      <div className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Nadesłane prace studentów
          </h3>

          <div className="flex items-center gap-2">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={selectedTaskId}
              onChange={(e) =>
                setSelectedTaskId(
                  e.target.value === "all" ? "all" : Number(e.target.value)
                )
              }
              className="bg-slate-900 border border-slate-800 text-slate-200 text-xs rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-indigo-500"
            >
              <option value="all">Wszystkie zadania</option>
              {tasks.map((t) => (
                <option key={t.id} value={t.id}>
                  #{t.id} {t.title}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="border border-slate-800 rounded-xl overflow-x-auto bg-slate-900/50">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-900/90 border-b border-slate-800 text-slate-400 uppercase tracking-wider text-[11px]">
              <tr>
                <th className="py-3 px-4 font-semibold">Student</th>
                <th className="py-3 px-4 font-semibold">Zadanie</th>
                <th className="py-3 px-4 font-semibold">Plik</th>
                <th className="py-3 px-4 font-semibold">Data nadesłania</th>
                <th className="py-3 px-4 font-semibold">Status / Ocena</th>
                <th className="py-3 px-4 font-semibold text-right">Akcje</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80">
              {filteredSubmissions.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-slate-500">
                    Brak nadesłanych prac dla wybranego filtru.
                  </td>
                </tr>
              ) : (
                filteredSubmissions.map((sub) => {
                  const task = tasks.find((t) => t.id === sub.task_id);
                  const isGrading = activeGradingSubId === sub.id;

                  return (
                    <React.Fragment key={sub.id}>
                      <tr className="hover:bg-slate-900/80 transition-colors">
                        <td className="py-3 px-4">
                          <div className="font-medium text-slate-200">
                            Student #{sub.student_id}
                          </div>
                        </td>
                        <td className="py-3 px-4 text-slate-300 max-w-xs truncate">
                          {task ? task.title : `#${sub.task_id}`}
                        </td>
                        <td className="py-3 px-4">
                          <div className="font-mono text-indigo-400">
                            {sub.original_filename}
                          </div>
                          <div className="text-[11px] text-slate-500">
                            {formatBytes(sub.size_bytes)}
                          </div>
                        </td>
                        <td className="py-3 px-4 text-slate-400">
                          {formatDateTime(sub.updated_at)}
                        </td>
                        <td className="py-3 px-4">
                          {sub.status === "graded" ? (
                            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                              <Award className="w-3.5 h-3.5" />
                              {sub.grade?.toFixed(1)}
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
                              <Clock className="w-3.5 h-3.5" />
                              Do oceny
                            </span>
                          )}
                        </td>
                        <td className="py-3 px-4 text-right">
                          <div className="inline-flex items-center gap-2">
                            <a
                              href={`/api/v1/submissions/${sub.id}/download`}
                              className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-slate-700 hover:bg-slate-800 text-slate-200 text-xs transition-colors"
                            >
                              <Download className="w-3.5 h-3.5" />
                              Pobierz
                            </a>
                            <button
                              onClick={() => {
                                setActiveGradingSubId(isGrading ? null : sub.id);
                                setGradeInput(sub.grade ?? 5.0);
                                setFeedbackInput(sub.feedback ?? "");
                                setGradeError(null);
                              }}
                              className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium transition-colors"
                            >
                              {isGrading
                                ? "Zamknij"
                                : sub.status === "graded"
                                ? "Zmień ocenę"
                                : "Wystaw ocenę"}
                            </button>
                          </div>
                        </td>
                      </tr>

                      {isGrading && (
                        <tr className="bg-slate-950/60 border-t border-slate-800">
                          <td colSpan={6} className="p-4">
                            <div className="max-w-xl space-y-3 bg-slate-900 border border-slate-800 p-4 rounded-xl">
                              <div className="flex items-center justify-between">
                                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                                  Wystawianie oceny: Student #{sub.student_id}
                                </h4>
                                <span className="text-xs text-slate-400 font-mono">
                                  {sub.original_filename}
                                </span>
                              </div>

                              {gradeError && (
                                <div className="p-2.5 bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs rounded-lg">
                                  {gradeError}
                                </div>
                              )}

                              <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
                                <div>
                                  <label className="block text-[11px] font-medium text-slate-400 mb-1">
                                    Ocena (2.0 - 5.0)
                                  </label>
                                  <select
                                    value={gradeInput}
                                    onChange={(e) =>
                                      setGradeInput(Number(e.target.value))
                                    }
                                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
                                  >
                                    <option value={2.0}>2.0</option>
                                    <option value={3.0}>3.0</option>
                                    <option value={3.5}>3.5</option>
                                    <option value={4.0}>4.0</option>
                                    <option value={4.5}>4.5</option>
                                    <option value={5.0}>5.0</option>
                                  </select>
                                </div>

                                <div className="sm:col-span-3">
                                  <label className="block text-[11px] font-medium text-slate-400 mb-1">
                                    Komentarz zwrotny
                                  </label>
                                  <input
                                    type="text"
                                    placeholder="Komentarz do pracy..."
                                    value={feedbackInput}
                                    onChange={(e) =>
                                      setFeedbackInput(e.target.value)
                                    }
                                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
                                  />
                                </div>
                              </div>

                              <div className="flex justify-end gap-2 pt-1">
                                <button
                                  type="button"
                                  onClick={() => setActiveGradingSubId(null)}
                                  className="px-3 py-1.5 rounded-lg border border-slate-800 text-xs text-slate-400 hover:text-slate-200"
                                >
                                  Anuluj
                                </button>
                                <button
                                  type="button"
                                  disabled={gradeSubmitting}
                                  onClick={() => handleSaveGrade(sub.id)}
                                  className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 text-white text-xs font-medium"
                                >
                                  {gradeSubmitting ? "Zapisywanie..." : "Zapisz ocenę"}
                                </button>
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {showTaskModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-slate-100">
                {editingTaskId !== null ? "Edytuj zadanie" : "Utwórz nowe zadanie"}
              </h3>
              <button
                onClick={() => setShowTaskModal(false)}
                className="text-slate-400 hover:text-slate-200 text-sm"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSaveTask} className="space-y-4">
              {formError && (
                <div className="p-2.5 bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs rounded-lg">
                  {formError}
                </div>
              )}

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Tytuł zadania
                </label>
                <input
                  type="text"
                  required
                  placeholder="np. Etap 3 - Implementacja testów"
                  value={taskTitle}
                  onChange={(e) => setTaskTitle(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Opis i wymagania
                </label>
                <textarea
                  rows={3}
                  placeholder="Opis zadania..."
                  value={taskDescription}
                  onChange={(e) => setTaskDescription(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Termin oddania (Deadline)
                </label>
                <input
                  type="datetime-local"
                  required
                  value={taskDeadline}
                  onChange={(e) => setTaskDeadline(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowTaskModal(false)}
                  className="px-3.5 py-1.5 rounded-lg border border-slate-800 text-xs text-slate-400 hover:text-slate-200"
                >
                  Anuluj
                </button>
                <button
                  type="submit"
                  disabled={taskSubmitting}
                  className="px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 text-white text-xs font-medium transition-colors"
                >
                  {taskSubmitting
                    ? "Zapisywanie..."
                    : editingTaskId !== null
                    ? "Zapisz zmiany"
                    : "Utwórz zadanie"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
