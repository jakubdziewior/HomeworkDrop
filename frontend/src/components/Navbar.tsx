"use client";

import React from "react";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import { LogOut, User as UserIcon, Shield, Activity } from "lucide-react";

export default function Navbar() {
  const { user, logout } = useAuth();

  return (
    <nav className="border-b border-slate-800 bg-slate-900/60 backdrop-blur-md sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-indigo-600 flex items-center justify-center text-white font-bold text-lg shadow-lg shadow-indigo-500/20">
            HD
          </div>
          <div>
            <span className="font-bold text-base tracking-tight text-white">
              HomeworkDrop
            </span>
            <span className="text-[10px] text-slate-400 block -mt-1 font-mono">
              Platforma prac projektowych
            </span>
          </div>
        </Link>

        <div className="flex items-center gap-4">
          <a
            href="http://127.0.0.1:8000/docs"
            target="_blank"
            rel="noreferrer"
            className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-800 text-xs text-slate-300 hover:text-white hover:border-slate-700 transition-colors"
          >
            <Activity className="w-3.5 h-3.5 text-emerald-400" />
            API Docs
          </a>

          {user ? (
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-800/80 rounded-lg border border-slate-700/60 text-xs">
                <UserIcon className="w-3.5 h-3.5 text-indigo-400" />
                <span className="font-medium text-slate-200">{user.fullName}</span>
                <span
                  className={`text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded ${
                    user.role === "teacher"
                      ? "bg-cyan-500/20 text-cyan-300"
                      : "bg-indigo-500/20 text-indigo-300"
                  }`}
                >
                  {user.role === "teacher" ? "Prowadzący" : "Student"}
                </span>
              </div>

              <button
                onClick={logout}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/20 text-xs font-medium transition-colors"
              >
                <LogOut className="w-3.5 h-3.5" />
                Wyloguj
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <Link
                href="/login?mode=login"
                className="px-3.5 py-1.5 rounded-lg text-xs font-medium text-slate-300 hover:text-white hover:bg-slate-800 transition-colors"
              >
                Logowanie
              </Link>
              <Link
                href="/login?mode=register"
                className="px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium transition-colors shadow-sm"
              >
                Rejestracja
              </Link>
            </div>
          )}
        </div>
      </div>
    </nav>
  );
}
