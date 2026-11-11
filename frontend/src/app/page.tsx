"use client";

import React from "react";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import {
  Lock,
  UserPlus,
  ArrowRight,
  ShieldCheck,
  Clock,
  UserCheck,
} from "lucide-react";

export default function Home() {
  const { user, isLoading } = useAuth();

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-20 text-center space-y-10">
      <div className="space-y-4">
        <h1 className="text-4xl sm:text-5xl font-extrabold text-white tracking-tight">
          HomeworkDrop
        </h1>
        <p className="text-base text-slate-400 max-w-xl mx-auto leading-relaxed">
          Platforma do bezpiecznego przesyłania i oceny zadań projektowych z
          automatyczną blokadą po upływie terminu.
        </p>
      </div>

      {!isLoading && (
        <div className="flex flex-wrap items-center justify-center gap-3">
          {user ? (
            <div className="space-y-4">
              <div className="text-xs text-slate-400">
                Zalogowano jako:{" "}
                <span className="font-semibold text-slate-200">
                  {user.fullName}
                </span>{" "}
                ({user.role === "teacher" ? "Prowadzący" : "Student"})
              </div>
              <div>
                <Link
                  href={user.role === "teacher" ? "/teacher" : "/student"}
                  className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs shadow-md transition-colors"
                >
                  Przejdź do swojego panelu
                  <ArrowRight className="w-4 h-4" />
                </Link>
              </div>
            </div>
          ) : (
            <>
              <Link
                href="/login?mode=login"
                className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs shadow-md transition-colors"
              >
                <Lock className="w-4 h-4" />
                Zaloguj się
              </Link>
              <Link
                href="/login?mode=register"
                className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-200 font-medium text-xs transition-colors"
              >
                <UserPlus className="w-4 h-4" />
                Zarejestruj konto
              </Link>
            </>
          )}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-8 border-t border-slate-800/80 text-left">
        <div className="p-4 bg-slate-900/60 border border-slate-800/80 rounded-xl space-y-2">
          <div className="w-8 h-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
            <ShieldCheck className="w-4 h-4" />
          </div>
          <h3 className="font-semibold text-xs text-white">
            Bezpieczne załączniki
          </h3>
          <p className="text-[11px] text-slate-400 leading-relaxed">
            Walidacja typów plików i twardy limit rozmiaru uploadu.
          </p>
        </div>

        <div className="p-4 bg-slate-900/60 border border-slate-800/80 rounded-xl space-y-2">
          <div className="w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
            <Clock className="w-4 h-4" />
          </div>
          <h3 className="font-semibold text-xs text-white">Blokada terminu</h3>
          <p className="text-[11px] text-slate-400 leading-relaxed">
            Automatyczne zamknięcie możliwości wysyłania prac po deadline.
          </p>
        </div>

        <div className="p-4 bg-slate-900/60 border border-slate-800/80 rounded-xl space-y-2">
          <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
            <UserCheck className="w-4 h-4" />
          </div>
          <h3 className="font-semibold text-xs text-white">Podział ról</h3>
          <p className="text-[11px] text-slate-400 leading-relaxed">
            Dedykowane uprawnienia i widoki dla studentów oraz prowadzących.
          </p>
        </div>
      </div>
    </div>
  );
}
