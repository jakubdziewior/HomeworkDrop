"use client";

import React, { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import {
  Lock,
  Mail,
  User as UserIcon,
  Check,
  X,
  AlertCircle,
  GraduationCap,
  BookOpen,
  ArrowRight,
} from "lucide-react";

function LoginFormContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login } = useAuth();

  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState<"student" | "teacher">("student");

  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const qMode = searchParams.get("mode");
    if (qMode === "register") {
      setMode("register");
    } else {
      setMode("login");
    }
  }, [searchParams]);

  const hasMinLength = password.length >= 8;
  const hasNumber = /\d/.test(password);
  const hasUpper = /[A-Z]/.test(password);
  const hasSpecial = /[!@#$%^&*(),.?":{}|<>]/.test(password);
  const isPasswordStrong = hasMinLength && hasNumber && hasUpper && hasSpecial;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccessMsg(null);

    if (mode === "register") {
      if (!fullName.trim() || !email.trim() || !password) {
        setError("Wypełnij wszystkie wymagane pola.");
        return;
      }
      if (!isPasswordStrong) {
        setError("Hasło nie spełnia wszystkich wymagań bezpieczeństwa.");
        return;
      }

      setLoading(true);
      try {
        const res = await fetch("http://127.0.0.1:8000/api/v1/auth/register", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: email.trim(),
            password: password,
            full_name: fullName.trim(),
            role: role,
          }),
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => null);
          throw new Error(
            errData?.detail || "Błąd podczas rejestracji użytkownika."
          );
        }

        setSuccessMsg(
          "Konto zostało pomyślnie zarejestrowane. Możesz się teraz zalogować."
        );
        setMode("login");
      } catch (err: any) {
        setError(err.message || "Nie udało się połączyć z serwerem API.");
      } finally {
        setLoading(false);
      }
    } else {
      if (!email.trim() || !password) {
        setError("Podaj adres email oraz hasło.");
        return;
      }

      setLoading(true);
      try {
        const res = await fetch("http://127.0.0.1:8000/api/v1/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: email.trim(),
            password: password,
          }),
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => null);
          throw new Error(
            errData?.detail || "Nieprawidłowy adres email lub hasło."
          );
        }

        const data = await res.json();
        login({
          id: data.user.id,
          email: data.user.email,
          fullName: data.user.full_name,
          role: data.user.role,
        });

        if (data.user.role === "teacher") {
          router.push("/teacher");
        } else {
          router.push("/student");
        }
      } catch (err: any) {
        setError(err.message || "Błąd logowania.");
      } finally {
        setLoading(false);
      }
    }
  };

  const handleDemoLogin = (demoRole: "student" | "teacher") => {
    if (demoRole === "student") {
      login({
        id: 1,
        email: "student@homeworkdrop.pl",
        fullName: "Jan Kowalski",
        role: "student",
      });
      router.push("/student");
    } else {
      login({
        id: 2,
        email: "teacher@homeworkdrop.pl",
        fullName: "dr inż. Mirosław Witkowski",
        role: "teacher",
      });
      router.push("/teacher");
    }
  };

  return (
    <div className="max-w-md w-full bg-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-8 shadow-2xl space-y-6">
      <div className="text-center space-y-2">
        <h2 className="text-2xl font-bold text-white tracking-tight">
          {mode === "login" ? "Zaloguj się do platformy" : "Zarejestruj konto"}
        </h2>
        <p className="text-xs text-slate-400">
          {mode === "login"
            ? "Wprowadź swoje poświadczenia, aby przejść do panelu zadań."
            : "Utwórz konto studenta lub prowadzącego z haszowaniem hasła bcrypt."}
        </p>
      </div>

      <div className="flex p-1 bg-slate-950 rounded-xl border border-slate-800">
        <button
          type="button"
          onClick={() => {
            setMode("login");
            setError(null);
          }}
          className={`flex-1 py-2 text-xs font-semibold rounded-lg transition-all ${
            mode === "login"
              ? "bg-indigo-600 text-white shadow-sm"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          Logowanie
        </button>
        <button
          type="button"
          onClick={() => {
            setMode("register");
            setError(null);
          }}
          className={`flex-1 py-2 text-xs font-semibold rounded-lg transition-all ${
            mode === "register"
              ? "bg-indigo-600 text-white shadow-sm"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          Rejestracja
        </button>
      </div>

      {error && (
        <div className="p-3 bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs rounded-xl flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {successMsg && (
        <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs rounded-xl flex items-center gap-2">
          <Check className="w-4 h-4 shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        {mode === "register" && (
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Imię i nazwisko
              </label>
              <div className="relative">
                <UserIcon className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
                <input
                  type="text"
                  required
                  placeholder="np. Jan Kowalski"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-9 pr-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
                />
              </div>
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Adres e-mail
            </label>
            <div className="relative">
              <Mail className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
              <input
                type="email"
                required
                placeholder="np. student@homeworkdrop.pl"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-9 pr-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Hasło dostępu
            </label>
            <div className="relative">
              <Lock className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
              <input
                type="password"
                required
                placeholder="••••••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-9 pr-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>

          {mode === "register" && (
            <div className="space-y-3 pt-1">
              <div className="p-3 bg-slate-950/80 border border-slate-800/80 rounded-xl space-y-1.5 text-[11px]">
                <div className="font-semibold text-slate-400 mb-1">
                  Wymagania dotyczące hasła:
                </div>
                <div className="flex items-center gap-1.5 text-slate-400">
                  {hasMinLength ? (
                    <Check className="w-3.5 h-3.5 text-emerald-400" />
                  ) : (
                    <X className="w-3.5 h-3.5 text-slate-600" />
                  )}
                  <span className={hasMinLength ? "text-emerald-300" : ""}>
                    Co najmniej 8 znaków
                  </span>
                </div>
                <div className="flex items-center gap-1.5 text-slate-400">
                  {hasNumber ? (
                    <Check className="w-3.5 h-3.5 text-emerald-400" />
                  ) : (
                    <X className="w-3.5 h-3.5 text-slate-600" />
                  )}
                  <span className={hasNumber ? "text-emerald-300" : ""}>
                    Co najmniej jedna cyfra
                  </span>
                </div>
                <div className="flex items-center gap-1.5 text-slate-400">
                  {hasUpper ? (
                    <Check className="w-3.5 h-3.5 text-emerald-400" />
                  ) : (
                    <X className="w-3.5 h-3.5 text-slate-600" />
                  )}
                  <span className={hasUpper ? "text-emerald-300" : ""}>
                    Co najmniej jedna wielka litera
                  </span>
                </div>
                <div className="flex items-center gap-1.5 text-slate-400">
                  {hasSpecial ? (
                    <Check className="w-3.5 h-3.5 text-emerald-400" />
                  ) : (
                    <X className="w-3.5 h-3.5 text-slate-600" />
                  )}
                  <span className={hasSpecial ? "text-emerald-300" : ""}>
                    Co najmniej jeden znak specjalny
                  </span>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Wybierz rolę
                </label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setRole("student")}
                    className={`p-2.5 rounded-xl border text-xs font-medium flex items-center justify-center gap-2 transition-all ${
                      role === "student"
                        ? "bg-indigo-600/20 border-indigo-500 text-indigo-300 shadow-sm"
                        : "bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    <GraduationCap className="w-4 h-4" />
                    Student
                  </button>
                  <button
                    type="button"
                    onClick={() => setRole("teacher")}
                    className={`p-2.5 rounded-xl border text-xs font-medium flex items-center justify-center gap-2 transition-all ${
                      role === "teacher"
                        ? "bg-cyan-600/20 border-cyan-500 text-cyan-300 shadow-sm"
                        : "bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    <BookOpen className="w-4 h-4" />
                    Prowadzący
                  </button>
                </div>
              </div>
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full inline-flex items-center justify-center gap-2 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 text-white text-xs font-semibold transition-colors shadow-sm"
          >
            {loading ? "Przetwarzanie..." : mode === "login" ? "Zaloguj się" : "Zarejestruj konto"}
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </form>

        <div className="pt-4 border-t border-slate-800/80 space-y-3">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 text-center">
            Szybkie logowanie testowe
          </div>
          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              onClick={() => handleDemoLogin("student")}
              className="p-2 bg-slate-950 border border-slate-800 hover:border-slate-700 rounded-xl text-slate-300 hover:text-white text-xs flex items-center justify-center gap-1.5 transition-colors"
            >
              <GraduationCap className="w-3.5 h-3.5 text-indigo-400" />
              Jako Student
            </button>
            <button
              type="button"
              onClick={() => handleDemoLogin("teacher")}
              className="p-2 bg-slate-950 border border-slate-800 hover:border-slate-700 rounded-xl text-slate-300 hover:text-white text-xs flex items-center justify-center gap-1.5 transition-colors"
            >
              <BookOpen className="w-3.5 h-3.5 text-cyan-400" />
              Jako Prowadzący
            </button>
          </div>
        </div>
      </div>
  );
}

export default function LoginPage() {
  return (
    <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center p-4">
      <Suspense
        fallback={
          <div className="p-8 text-center text-slate-400 text-xs">
            Ładowanie formularza...
          </div>
        }
      >
        <LoginFormContent />
      </Suspense>
    </div>
  );
}
