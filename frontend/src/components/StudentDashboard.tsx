"use client";

import React, { useState } from "react";
import {
  UploadCloud,
  FileCheck,
  Clock,
  CheckCircle2,
  AlertCircle,
  FileText,
  Calendar,
  Award,
  ChevronRight,
} from "lucide-react";

export interface TaskItem {
  id: number;
  title: string;
  description: string;
  deadline: string;
  teacherName: string;
  status: "pending" | "submitted" | "graded";
  submittedFile?: string;
  submissionDate?: string;
  grade?: number;
  feedback?: string;
}

const INITIAL_STUDENT_TASKS: TaskItem[] = [
  {
    id: 1,
    title: "Implementacja potoku CI/CD z testami bezpieczeństwa",
    description:
      "Przygotowanie pliku konfiguracyjnego GitHub Actions uruchamiającego testy jednostkowe oraz skanowanie SAST.",
    deadline: new Date(Date.now() + 1000 * 60 * 60 * 72).toISOString(),
    teacherName: "dr inż. Mirosław Witkowski",
    status: "pending",
  },
  {
    id: 2,
    title: "Projekt bazy danych i model zagrożeń STRIDE",
    description:
      "Stworzenie diagramu ERD oraz pełnej matrycy zagrożeń dla platformy oddawania projektów.",
    deadline: new Date(Date.now() + 1000 * 60 * 60 * 24 * 7).toISOString(),
    teacherName: "dr inż. Mirosław Witkowski",
    status: "pending",
  },
  {
    id: 3,
    title: "Wstępna analiza podatności aplikacji webowej",
    description:
      "Raport ze skanowania podatności z wykorzystaniem narzędzia OWASP ZAP.",
    deadline: new Date(Date.now() - 1000 * 60 * 60 * 12).toISOString(),
    teacherName: "dr inż. Mirosław Witkowski",
    status: "graded",
    submittedFile: "raport_owasp_zap_kowalski.pdf",
    submissionDate: new Date(Date.now() - 1000 * 60 * 60 * 16).toISOString(),
    grade: 5.0,
    feedback: "Bardzo szczegółowy raport z właściwą klasyfikacją podatności.",
  },
];

export default function StudentDashboard() {
  const [tasks, setTasks] = useState<TaskItem[]>(INITIAL_STUDENT_TASKS);
  const [selectedTask, setSelectedTask] = useState<TaskItem | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
      setUploadStatus(null);
    }
  };

  const handleUploadSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTask || !selectedFile) {
      setUploadStatus("Wybierz plik do przesłania.");
      return;
    }

    const isExpired = new Date(selectedTask.deadline).getTime() < Date.now();
    if (isExpired) {
      setUploadStatus("Termin przesyłania rozwiązań dla tego zadania upłynął.");
      return;
    }

    setIsSubmitting(true);
    setTimeout(() => {
      setTasks((prev) =>
        prev.map((t) =>
          t.id === selectedTask.id
            ? {
                ...t,
                status: "submitted",
                submittedFile: selectedFile.name,
                submissionDate: new Date().toISOString(),
              }
            : t
        )
      );
      setIsSubmitting(false);
      setUploadStatus("Plik został pomyślnie przesłany do weryfikacji.");
      setSelectedFile(null);
    }, 600);
  };

  const formatDateTime = (isoString: string) => {
    const d = new Date(isoString);
    return d.toLocaleString("pl-PL", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const isPastDeadline = (isoString: string) => {
    return new Date(isoString).getTime() < Date.now();
  };

  return (
    <div className="space-y-6">
      <header className="border-b border-slate-800 pb-5">
        <h2 className="text-2xl font-bold text-slate-100">Panel Studenta</h2>
        <p className="text-sm text-slate-400 mt-1">
          Zarządzaj swoimi zadaniami, wgrywaj rozwiązania i monitoruj oceny.
        </p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
              Lista zadań do wykonania ({tasks.length})
            </h3>
          </div>

          <div className="space-y-3">
            {tasks.map((task) => {
              const expired = isPastDeadline(task.deadline);
              const isSelected = selectedTask?.id === task.id;

              return (
                <div
                  key={task.id}
                  onClick={() => {
                    setSelectedTask(task);
                    setSelectedFile(null);
                    setUploadStatus(null);
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
                        <h4 className="font-semibold text-slate-100 text-base">
                          {task.title}
                        </h4>
                      </div>
                      <p className="text-sm text-slate-400 leading-relaxed line-clamp-2">
                        {task.description}
                      </p>
                    </div>

                    <div className="shrink-0 flex flex-col items-end gap-2">
                      {task.status === "graded" && (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                          <Award className="w-3.5 h-3.5" />
                          Ocena: {task.grade?.toFixed(1)}
                        </span>
                      )}
                      {task.status === "submitted" && (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-500/10 text-blue-400 border border-blue-500/20">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          Przesłano
                        </span>
                      )}
                      {task.status === "pending" && !expired && (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
                          <Clock className="w-3.5 h-3.5" />
                          Oczekuje
                        </span>
                      )}
                      {task.status === "pending" && expired && (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-rose-500/10 text-rose-400 border border-rose-500/20">
                          <AlertCircle className="w-3.5 h-3.5" />
                          Po terminie
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="mt-4 pt-3 border-t border-slate-800/60 flex flex-wrap items-center justify-between gap-3 text-xs text-slate-400">
                    <div className="flex items-center gap-1.5">
                      <Calendar className="w-4 h-4 text-slate-500" />
                      <span>Termin:</span>
                      <span
                        className={`font-medium ${
                          expired ? "text-rose-400" : "text-slate-200"
                        }`}
                      >
                        {formatDateTime(task.deadline)}
                      </span>
                    </div>

                    <div className="text-slate-400">
                      Prowadzący: {task.teacherName}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="space-y-4">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
            Szczegóły i przesyłanie rozwiązania
          </h3>

          {selectedTask ? (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-5">
              <div>
                <h4 className="font-semibold text-slate-100 text-lg mb-1">
                  {selectedTask.title}
                </h4>
                <p className="text-sm text-slate-400 leading-relaxed">
                  {selectedTask.description}
                </p>
              </div>

              {selectedTask.status === "graded" && (
                <div className="p-4 bg-emerald-950/30 border border-emerald-500/30 rounded-lg space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs uppercase font-semibold text-emerald-400">
                      Ocena końcowa
                    </span>
                    <span className="text-xl font-bold text-emerald-300">
                      {selectedTask.grade?.toFixed(1)} / 5.0
                    </span>
                  </div>
                  {selectedTask.feedback && (
                    <div className="text-xs text-emerald-200/90 pt-2 border-t border-emerald-500/20">
                      <span className="font-medium text-emerald-300">Komentarz: </span>
                      {selectedTask.feedback}
                    </div>
                  )}
                </div>
              )}

              {selectedTask.submittedFile && (
                <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-lg flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <FileText className="w-4 h-4 text-indigo-400" />
                    <div>
                      <div className="font-medium text-slate-200">
                        {selectedTask.submittedFile}
                      </div>
                      <div className="text-slate-500">
                        Przesłano:{" "}
                        {selectedTask.submissionDate
                          ? formatDateTime(selectedTask.submissionDate)
                          : "-"}
                      </div>
                    </div>
                  </div>
                  <span className="text-emerald-400 font-medium">Zapisano</span>
                </div>
              )}

              <form onSubmit={handleUploadSubmit} className="space-y-4 pt-2">
                <div className="space-y-2">
                  <label className="block text-xs font-medium text-slate-300">
                    Wgraj plik z rozwiązaniem (np. .zip, .pdf, .py, .tar.gz)
                  </label>
                  <label
                    className={`flex flex-col items-center justify-center p-6 border-2 border-dashed rounded-xl cursor-pointer transition-colors ${
                      isPastDeadline(selectedTask.deadline)
                        ? "border-slate-800 bg-slate-950/30 cursor-not-allowed opacity-60"
                        : "border-slate-700 hover:border-indigo-500 bg-slate-950/50"
                    }`}
                  >
                    <UploadCloud className="w-8 h-8 text-slate-400 mb-2" />
                    <span className="text-xs font-medium text-slate-300">
                      {selectedFile ? selectedFile.name : "Wybierz plik z dysku"}
                    </span>
                    <span className="text-[11px] text-slate-500 mt-1">
                      Maksymalny dozwolony rozmiar: 10 MB
                    </span>
                    <input
                      type="file"
                      className="hidden"
                      disabled={isPastDeadline(selectedTask.deadline) || isSubmitting}
                      onChange={handleFileChange}
                    />
                  </label>
                </div>

                {uploadStatus && (
                  <div
                    className={`p-3 rounded-lg text-xs ${
                      uploadStatus.includes("pomyślnie")
                        ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                        : "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                    }`}
                  >
                    {uploadStatus}
                  </div>
                )}

                <button
                  type="submit"
                  disabled={
                    !selectedFile ||
                    isSubmitting ||
                    isPastDeadline(selectedTask.deadline)
                  }
                  className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 disabled:text-slate-600 text-white font-medium text-sm transition-colors shadow-sm"
                >
                  <FileCheck className="w-4 h-4" />
                  {isSubmitting ? "Wgrywanie pliku..." : "Wyślij rozwiązanie"}
                </button>
              </form>
            </div>
          ) : (
            <div className="bg-slate-900 border border-slate-800/80 rounded-xl p-8 text-center text-slate-500 text-sm">
              Wybierz zadanie z listy po lewej stronie, aby wyświetlić szczegóły i formularz wgrywania pliku.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
