"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import {
  ALLOWED_EXTENSIONS,
  ApiSubmission,
  ApiTask,
  MAX_UPLOAD_SIZE_BYTES,
  apiRequest,
  extractErrorMessage,
} from "@/lib/api";
import {
  UploadCloud,
  FileCheck,
  Clock,
  CheckCircle2,
  AlertCircle,
  FileText,
  Calendar,
  Award,
  Lock,
  Download,
  RefreshCw,
} from "lucide-react";

interface StudentTaskRow {
  task: ApiTask;
  submission: ApiSubmission | null;
}

function formatDateTime(isoString: string): string {
  return new Date(isoString).toLocaleString("pl-PL", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

export default function StudentDashboard() {
  const { user, isLoading } = useAuth();
  const [rows, setRows] = useState<StudentTaskRow[]>([]);
  const [dataLoading, setDataLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [selectedTaskId, setSelectedTaskId] = useState<number | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadFeedback, setUploadFeedback] = useState<{
    type: "success" | "error";
    text: string;
  } | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const loadTasks = useCallback(async () => {
    setDataLoading(true);
    setLoadError(null);
    try {
      const tasks = await apiRequest<ApiTask[]>(
        "/api/v1/tasks",
        {},
        "Nie udało się pobrać listy zadań."
      );
      const loaded = await Promise.all(
        tasks.map(async (task): Promise<StudentTaskRow> => {
          try {
            const res = await fetch(`/api/v1/tasks/${task.id}/submissions/me`, {
              credentials: "same-origin",
              cache: "no-store",
            });
            if (res.ok) {
              return { task, submission: (await res.json()) as ApiSubmission };
            }
            return { task, submission: null };
          } catch {
            return { task, submission: null };
          }
        })
      );
      setRows(loaded);
    } catch (err: unknown) {
      setLoadError(err instanceof Error ? err.message : "Błąd pobierania danych.");
    } finally {
      setDataLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!isLoading && user?.role === "student") {
      loadTasks();
    }
  }, [isLoading, user, loadTasks]);

  if (isLoading) {
    return (
      <div className="max-w-md mx-auto my-16 p-8 text-center text-xs text-slate-400">
        Ładowanie panelu studenta...
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
          Dostęp do panelu studenta wymaga zalogowania na konto studenckie.
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

  if (user.role === "teacher") {
    return (
      <div className="max-w-md mx-auto my-16 p-8 bg-slate-900 border border-slate-800 rounded-2xl text-center space-y-4 shadow-xl">
        <h2 className="text-xl font-bold text-white">Panel Studenta</h2>
        <p className="text-xs text-slate-400">
          Jesteś zalogowany jako Prowadzący. Ten widok jest przeznaczony dla studentów.
        </p>
        <Link
          href="/teacher"
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs transition-colors shadow-sm"
        >
          Przejdź do Panelu Prowadzącego
        </Link>
      </div>
    );
  }

  const selectedRow = rows.find((r) => r.task.id === selectedTaskId) ?? null;

  const isExpired = (task: ApiTask) =>
    task.is_expired || new Date(task.deadline).getTime() <= Date.now();

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] ?? null;
    setSelectedFile(file);
    setUploadFeedback(null);
  };

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedRow || !selectedFile) {
      setUploadFeedback({ type: "error", text: "Wybierz plik do przesłania." });
      return;
    }

    if (isExpired(selectedRow.task)) {
      setUploadFeedback({
        type: "error",
        text: "Termin przesyłania rozwiązań dla tego zadania upłynął.",
      });
      return;
    }

    if (selectedRow.submission?.status === "graded") {
      setUploadFeedback({
        type: "error",
        text: "Zgłoszenie zostało już ocenione – nie można podmienić pliku.",
      });
      return;
    }

    const lowerName = selectedFile.name.toLowerCase();
    const hasAllowedExt = ALLOWED_EXTENSIONS.some((ext) => lowerName.endsWith(ext));
    if (!hasAllowedExt) {
      setUploadFeedback({
        type: "error",
        text: `Niedozwolone rozszerzenie pliku. Dozwolone: ${ALLOWED_EXTENSIONS.join(", ")}.`,
      });
      return;
    }

    if (selectedFile.size === 0) {
      setUploadFeedback({ type: "error", text: "Przesyłany plik jest pusty." });
      return;
    }

    if (selectedFile.size > MAX_UPLOAD_SIZE_BYTES) {
      setUploadFeedback({
        type: "error",
        text: "Przesyłany plik jest za duży. Maksymalny rozmiar to 10 MB.",
      });
      return;
    }

    setIsSubmitting(true);
    setUploadFeedback(null);

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);

      const res = await fetch(`/api/v1/tasks/${selectedRow.task.id}/submissions`, {
        method: "POST",
        credentials: "same-origin",
        body: formData,
      });

      if (!res.ok) {
        const errBody = await res.json().catch(() => null);
        throw new Error(extractErrorMessage(errBody, "Nie udało się przesłać pliku."));
      }

      const savedSubmission = (await res.json()) as ApiSubmission;
      setRows((prev) =>
        prev.map((row) =>
          row.task.id === selectedRow.task.id
            ? { ...row, submission: savedSubmission }
            : row
        )
      );
      setSelectedFile(null);
      setUploadFeedback({
        type: "success",
        text: "Plik został pomyślnie przesłany do weryfikacji.",
      });
    } catch (err: unknown) {
      setUploadFeedback({
        type: "error",
        text: err instanceof Error ? err.message : "Błąd podczas wysyłania pliku.",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const selectedExpired = selectedRow ? isExpired(selectedRow.task) : false;
  const selectedGraded = selectedRow?.submission?.status === "graded";
  const uploadDisabled = selectedExpired || selectedGraded || isSubmitting;

  return (
    <div className="space-y-6">
      <header className="border-b border-slate-800 pb-4 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-100">Panel Studenta</h2>
          <p className="text-xs text-slate-400 mt-1">
            Zadania do wykonania oraz formularz wgrywania rozwiązań.
          </p>
        </div>
        <button
          type="button"
          onClick={loadTasks}
          disabled={dataLoading}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-800 text-xs text-slate-300 hover:text-white hover:border-slate-700 disabled:opacity-50 transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${dataLoading ? "animate-spin" : ""}`} />
          Odśwież
        </button>
      </header>

      {loadError && (
        <div className="p-3 bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs rounded-xl flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{loadError}</span>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Aktywne zadania ({rows.length})
            </h3>
          </div>

          {dataLoading && rows.length === 0 ? (
            <div className="p-8 bg-slate-900/40 border border-slate-800 rounded-xl text-center text-xs text-slate-500">
              Pobieranie listy zadań...
            </div>
          ) : rows.length === 0 ? (
            <div className="p-8 bg-slate-900/40 border border-slate-800 rounded-xl text-center text-xs text-slate-500">
              Brak dostępnych zadań w systemie.
            </div>
          ) : (
            <div className="space-y-3">
              {rows.map(({ task, submission }) => {
                const expired = isExpired(task);
                const isSelected = selectedTaskId === task.id;

                return (
                  <div
                    key={task.id}
                    onClick={() => {
                      setSelectedTaskId(task.id);
                      setSelectedFile(null);
                      setUploadFeedback(null);
                    }}
                    className={`p-5 rounded-xl border transition-all cursor-pointer bg-slate-900/60 hover:bg-slate-900/90 ${
                      isSelected
                        ? "border-indigo-500 shadow-lg shadow-indigo-500/10 ring-1 ring-indigo-500"
                        : "border-slate-800/80 hover:border-slate-700"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-mono text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded">
                            #{task.id}
                          </span>
                          <h4 className="font-semibold text-slate-100 text-sm">
                            {task.title}
                          </h4>
                        </div>
                        <p className="text-xs text-slate-400 leading-relaxed line-clamp-2">
                          {task.description || "Brak dodatkowego opisu."}
                        </p>
                      </div>

                      <div className="shrink-0 flex flex-col items-end gap-2">
                        {submission?.status === "graded" && (
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                            <Award className="w-3.5 h-3.5" />
                            Ocena: {submission.grade?.toFixed(1)}
                          </span>
                        )}
                        {submission?.status === "submitted" && (
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-500/10 text-blue-400 border border-blue-500/20">
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            Przesłano
                          </span>
                        )}
                        {!submission && !expired && (
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
                            <Clock className="w-3.5 h-3.5" />
                            Oczekuje
                          </span>
                        )}
                        {!submission && expired && (
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-rose-500/10 text-rose-400 border border-rose-500/20">
                            <AlertCircle className="w-3.5 h-3.5" />
                            Po terminie
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="mt-4 pt-3 border-t border-slate-800/60 flex flex-wrap items-center justify-between gap-3 text-xs text-slate-400">
                      <div className="flex items-center gap-1.5">
                        <Calendar className="w-3.5 h-3.5 text-slate-500" />
                        <span>Termin:</span>
                        <span
                          className={`font-medium ${
                            expired ? "text-rose-400" : "text-slate-200"
                          }`}
                        >
                          {formatDateTime(task.deadline)}
                        </span>
                      </div>

                      {submission && (
                        <div className="text-slate-400 text-xs font-mono">
                          {submission.original_filename}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <div className="space-y-4">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Wgrywanie rozwiązania
          </h3>

          {selectedRow ? (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
              <div>
                <h4 className="font-semibold text-slate-100 text-base mb-1">
                  {selectedRow.task.title}
                </h4>
                <p className="text-xs text-slate-400 leading-relaxed">
                  {selectedRow.task.description || "Brak opisu."}
                </p>
              </div>

              {selectedRow.submission?.status === "graded" && (
                <div className="p-3 bg-emerald-950/30 border border-emerald-500/30 rounded-lg space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs uppercase font-semibold text-emerald-400">
                      Ocena końcowa
                    </span>
                    <span className="text-lg font-bold text-emerald-300">
                      {selectedRow.submission.grade?.toFixed(1)} / 5.0
                    </span>
                  </div>
                  {selectedRow.submission.feedback && (
                    <div className="text-xs text-emerald-200/90 pt-1.5 border-t border-emerald-500/20">
                      <span className="font-medium text-emerald-300">Komentarz: </span>
                      {selectedRow.submission.feedback}
                    </div>
                  )}
                </div>
              )}

              {selectedRow.submission && (
                <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-lg flex items-center justify-between gap-2 text-xs">
                  <div className="flex items-center gap-2 min-w-0">
                    <FileText className="w-4 h-4 text-indigo-400 shrink-0" />
                    <div className="min-w-0">
                      <div className="font-medium text-slate-200 truncate">
                        {selectedRow.submission.original_filename}
                      </div>
                      <div className="text-slate-500 text-[11px]">
                        {formatBytes(selectedRow.submission.size_bytes)} &bull;{" "}
                        {formatDateTime(selectedRow.submission.updated_at)}
                      </div>
                    </div>
                  </div>
                  <a
                    href={`/api/v1/submissions/${selectedRow.submission.id}/download`}
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-200 text-[11px] font-medium shrink-0 transition-colors"
                  >
                    <Download className="w-3 h-3" />
                    Pobierz
                  </a>
                </div>
              )}

              {selectedExpired && (
                <div className="p-3 bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs rounded-lg flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>
                    Termin przesyłania prac upłynął ({formatDateTime(selectedRow.task.deadline)}). Wgrywanie rozwiązań zostało automatycznie zablokowane.
                  </span>
                </div>
              )}

              {!selectedExpired && selectedGraded && (
                <div className="p-3 bg-blue-500/10 border border-blue-500/20 text-blue-300 text-xs rounded-lg flex items-center gap-2">
                  <Award className="w-4 h-4 shrink-0" />
                  <span>
                    Praca została już oceniona. Podmiana pliku jest zablokowana.
                  </span>
                </div>
              )}

              <form onSubmit={handleUploadSubmit} className="space-y-4 pt-1">
                <div className="space-y-2">
                  <label className="block text-xs font-medium text-slate-300">
                    Plik z rozwiązaniem ({ALLOWED_EXTENSIONS.join(", ")})
                  </label>
                  <label
                    className={`flex flex-col items-center justify-center p-5 border-2 border-dashed rounded-xl transition-colors ${
                      uploadDisabled
                        ? "border-slate-800 bg-slate-950/30 cursor-not-allowed opacity-60"
                        : "border-slate-700 hover:border-indigo-500 bg-slate-950/50 cursor-pointer"
                    }`}
                  >
                    <UploadCloud className="w-7 h-7 text-slate-400 mb-1" />
                    <span className="text-xs font-medium text-slate-300 text-center break-all">
                      {selectedFile ? selectedFile.name : "Wybierz plik z dysku"}
                    </span>
                    <span className="text-[11px] text-slate-500 mt-0.5">
                      Limit rozmiaru: 10 MB
                    </span>
                    <input
                      type="file"
                      accept={ALLOWED_EXTENSIONS.join(",")}
                      className="hidden"
                      disabled={uploadDisabled}
                      onChange={handleFileChange}
                    />
                  </label>
                </div>

                {uploadFeedback && (
                  <div
                    className={`p-2.5 rounded-lg text-xs ${
                      uploadFeedback.type === "success"
                        ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                        : "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                    }`}
                  >
                    {uploadFeedback.text}
                  </div>
                )}

                <button
                  type="submit"
                  disabled={!selectedFile || uploadDisabled}
                  className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 disabled:text-slate-600 text-white font-medium text-xs transition-colors shadow-sm"
                >
                  <FileCheck className="w-4 h-4" />
                  {isSubmitting
                    ? "Wgrywanie..."
                    : selectedRow.submission
                    ? "Zastąp rozwiązanie"
                    : "Wyślij rozwiązanie"}
                </button>
              </form>
            </div>
          ) : (
            <div className="bg-slate-900 border border-slate-800/80 rounded-xl p-6 text-center text-slate-500 text-xs">
              Wybierz zadanie z listy, aby wyświetlić szczegóły i formularz wgrywania.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
