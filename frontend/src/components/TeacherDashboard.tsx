"use client";

import React, { useState } from "react";
import {
  PlusCircle,
  Users,
  CheckCircle2,
  Clock,
  Calendar,
  FileText,
  Award,
  Search,
  Filter,
} from "lucide-react";

export interface TeacherTask {
  id: number;
  title: string;
  description: string;
  deadline: string;
  submissionsCount: number;
  createdAt: string;
}

export interface StudentSubmission {
  id: number;
  taskId: number;
  studentName: string;
  studentEmail: string;
  fileName: string;
  submittedAt: string;
  grade?: number;
  feedback?: string;
  status: "submitted" | "graded";
}

const INITIAL_TEACHER_TASKS: TeacherTask[] = [
  {
    id: 1,
    title: "Implementacja potoku CI/CD z testami bezpieczeństwa",
    description:
      "Przygotowanie pliku konfiguracyjnego GitHub Actions uruchamiającego testy jednostkowe oraz skanowanie SAST.",
    deadline: new Date(Date.now() + 1000 * 60 * 60 * 72).toISOString(),
    submissionsCount: 2,
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 48).toISOString(),
  },
  {
    id: 2,
    title: "Wstępna analiza podatności aplikacji webowej",
    description:
      "Raport ze skanowania podatności z wykorzystaniem narzędzia OWASP ZAP.",
    deadline: new Date(Date.now() - 1000 * 60 * 60 * 12).toISOString(),
    submissionsCount: 1,
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 96).toISOString(),
  },
];

const INITIAL_SUBMISSIONS: StudentSubmission[] = [
  {
    id: 101,
    taskId: 1,
    studentName: "Jan Kowalski",
    studentEmail: "j.kowalski@student.polsl.pl",
    fileName: "ci_cd_pipeline_kowalski.zip",
    submittedAt: new Date(Date.now() - 1000 * 60 * 60 * 5).toISOString(),
    status: "submitted",
  },
  {
    id: 102,
    taskId: 1,
    studentName: "Anna Nowak",
    studentEmail: "a.nowak@student.polsl.pl",
    fileName: "security_actions_nowak.zip",
    submittedAt: new Date(Date.now() - 1000 * 60 * 60 * 18).toISOString(),
    status: "submitted",
  },
  {
    id: 103,
    taskId: 2,
    studentName: "Piotr Wiśniewski",
    studentEmail: "p.wisniewski@student.polsl.pl",
    fileName: "raport_owasp_zap_wisniewski.pdf",
    submittedAt: new Date(Date.now() - 1000 * 60 * 60 * 16).toISOString(),
    grade: 5.0,
    feedback: "Bardzo szczegółowy raport z właściwą klasyfikacją podatności.",
    status: "graded",
  },
];

export default function TeacherDashboard() {
  const [tasks, setTasks] = useState<TeacherTask[]>(INITIAL_TEACHER_TASKS);
  const [submissions, setSubmissions] =
    useState<StudentSubmission[]>(INITIAL_SUBMISSIONS);
  const [selectedTaskId, setSelectedTaskId] = useState<number | "all">("all");
  const [showCreateModal, setShowCreateModal] = useState(false);

  const [newTitle, setNewTitle] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [newDeadline, setNewDeadline] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  const [activeGradingSubId, setActiveGradingSubId] = useState<number | null>(
    null
  );
  const [gradeInput, setGradeInput] = useState<number>(5.0);
  const [feedbackInput, setFeedbackInput] = useState<string>("");

  const handleCreateTask = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim() || !newDescription.trim() || !newDeadline.trim()) {
      setFormError("Wszystkie pola są wymagane.");
      return;
    }

    const newTask: TeacherTask = {
      id: tasks.length + 1,
      title: newTitle.trim(),
      description: newDescription.trim(),
      deadline: new Date(newDeadline).toISOString(),
      submissionsCount: 0,
      createdAt: new Date().toISOString(),
    };

    setTasks([newTask, ...tasks]);
    setNewTitle("");
    setNewDescription("");
    setNewDeadline("");
    setFormError(null);
    setShowCreateModal(false);
  };

  const handleSaveGrade = (submissionId: number) => {
    if (gradeInput < 2.0 || gradeInput > 5.0) {
      return;
    }

    setSubmissions((prev) =>
      prev.map((sub) =>
        sub.id === submissionId
          ? {
              ...sub,
              grade: gradeInput,
              feedback: feedbackInput.trim() || undefined,
              status: "graded",
            }
          : sub
      )
    );
    setActiveGradingSubId(null);
    setFeedbackInput("");
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

  const filteredSubmissions =
    selectedTaskId === "all"
      ? submissions
      : submissions.filter((s) => s.taskId === selectedTaskId);

  return (
    <div className="space-y-6">
      <header className="border-b border-slate-800 pb-5 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-100">
            Panel Prowadzącego
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            Zarządzaj tematami zadań, przeglądaj nadesłane prace i wystawiaj oceny.
          </p>
        </div>

        <button
          onClick={() => setShowCreateModal(true)}
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm transition-colors shadow-sm"
        >
          <PlusCircle className="w-4 h-4" />
          Utwórz nowe zadanie
        </button>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-4 bg-slate-900 border border-slate-800 rounded-xl">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium uppercase">
            <span>Aktywne zadania</span>
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
            <span>Ocenione zgłoszenia</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-slate-100 mt-2">
            {submissions.filter((s) => s.status === "graded").length} /{" "}
            {submissions.length}
          </div>
        </div>
      </div>

      <div className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
            Lista nadesłanych prac studentów
          </h3>

          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-slate-400" />
            <select
              value={selectedTaskId}
              onChange={(e) =>
                setSelectedTaskId(
                  e.target.value === "all" ? "all" : Number(e.target.value)
                )
              }
              className="bg-slate-900 border border-slate-800 text-slate-200 text-xs rounded-lg px-3 py-1.5 focus:outline-none focus:border-indigo-500"
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

        <div className="border border-slate-800 rounded-xl overflow-hidden bg-slate-900/50">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-900/90 border-b border-slate-800 text-slate-400 uppercase tracking-wider">
              <tr>
                <th className="py-3.5 px-4 font-semibold">Student</th>
                <th className="py-3.5 px-4 font-semibold">Zadanie</th>
                <th className="py-3.5 px-4 font-semibold">Plik</th>
                <th className="py-3.5 px-4 font-semibold">Data nadesłania</th>
                <th className="py-3.5 px-4 font-semibold">Status / Ocena</th>
                <th className="py-3.5 px-4 font-semibold text-right">Akcja</th>
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
                  const task = tasks.find((t) => t.id === sub.taskId);
                  const isGrading = activeGradingSubId === sub.id;

                  return (
                    <React.Fragment key={sub.id}>
                      <tr className="hover:bg-slate-900/80 transition-colors">
                        <td className="py-3 px-4">
                          <div className="font-medium text-slate-200">
                            {sub.studentName}
                          </div>
                          <div className="text-slate-500 text-[11px]">
                            {sub.studentEmail}
                          </div>
                        </td>
                        <td className="py-3 px-4 text-slate-300 max-w-xs truncate">
                          {task ? task.title : `#${sub.taskId}`}
                        </td>
                        <td className="py-3 px-4 font-mono text-indigo-400">
                          {sub.fileName}
                        </td>
                        <td className="py-3 px-4 text-slate-400">
                          {formatDateTime(sub.submittedAt)}
                        </td>
                        <td className="py-3 px-4">
                          {sub.status === "graded" ? (
                            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                              <Award className="w-3.5 h-3.5" />
                              {sub.grade?.toFixed(1)}
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
                              <Clock className="w-3.5 h-3.5" />
                              Do oceny
                            </span>
                          )}
                        </td>
                        <td className="py-3 px-4 text-right">
                          <button
                            onClick={() => {
                              setActiveGradingSubId(
                                isGrading ? null : sub.id
                              );
                              setGradeInput(sub.grade || 5.0);
                              setFeedbackInput(sub.feedback || "");
                            }}
                            className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium transition-colors"
                          >
                            {isGrading
                              ? "Zamknij"
                              : sub.status === "graded"
                              ? "Zmień ocenę"
                              : "Wystaw ocenę"}
                          </button>
                        </td>
                      </tr>

                      {isGrading && (
                        <tr className="bg-slate-950/60 border-t border-slate-800">
                          <td colSpan={6} className="p-4">
                            <div className="max-w-xl space-y-3 bg-slate-900 border border-slate-800 p-4 rounded-xl">
                              <div className="flex items-center justify-between">
                                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                                  Wystawianie oceny dla: {sub.studentName}
                                </h4>
                                <span className="text-xs text-slate-400">
                                  Plik: {sub.fileName}
                                </span>
                              </div>

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
                                    <option value={2.0}>2.0 (Niedostateczny)</option>
                                    <option value={3.0}>3.0 (Dostateczny)</option>
                                    <option value={3.5}>3.5 (Dość dobry)</option>
                                    <option value={4.0}>4.0 (Dobry)</option>
                                    <option value={4.5}>4.5 (Ponad dobry)</option>
                                    <option value={5.0}>5.0 (Bardzo dobry)</option>
                                  </select>
                                </div>

                                <div className="sm:col-span-3">
                                  <label className="block text-[11px] font-medium text-slate-400 mb-1">
                                    Komentarz zwrotny (opcjonalny)
                                  </label>
                                  <input
                                    type="text"
                                    placeholder="np. Dobrze przygotowana konfiguracja..."
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
                                  onClick={() => handleSaveGrade(sub.id)}
                                  className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium"
                                >
                                  Zapisz ocenę
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

      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-lg font-bold text-slate-100">
                Utwórz nowe zadanie dla studentów
              </h3>
              <button
                onClick={() => setShowCreateModal(false)}
                className="text-slate-400 hover:text-slate-200 text-sm"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateTask} className="space-y-4">
              {formError && (
                <div className="p-3 bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs rounded-lg">
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
                  placeholder="np. Etap 2 - Implementacja aplikacji"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Opis i wymagania
                </label>
                <textarea
                  required
                  rows={3}
                  placeholder="Szczegółowy opis wymagań projektu..."
                  value={newDescription}
                  onChange={(e) => setNewDescription(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Ostateczny termin oddania (Deadline)
                </label>
                <input
                  type="datetime-local"
                  required
                  value={newDeadline}
                  onChange={(e) => setNewDeadline(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 rounded-lg border border-slate-800 text-xs font-medium text-slate-400 hover:text-slate-200"
                >
                  Anuluj
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium transition-colors"
                >
                  Utwórz zadanie
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
