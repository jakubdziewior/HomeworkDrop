import Link from "next/link";
import { GraduationCap, BookOpen, ShieldCheck, ArrowRight, Activity } from "lucide-react";

export default function Home() {
  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-between">
      <header className="border-b border-slate-800/80 bg-slate-900/40 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
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
          </div>

          <div className="flex items-center gap-3">
            <a
              href="http://127.0.0.1:8000/docs"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-800 text-xs text-slate-300 hover:text-white hover:border-slate-700 transition-colors"
            >
              <Activity className="w-3.5 h-3.5 text-emerald-400" />
              API Swagger
            </a>
          </div>
        </div>
      </header>

      <section className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-16 text-center space-y-6">
        <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full text-xs font-medium bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
          <ShieldCheck className="w-3.5 h-3.5" />
          Bezpieczne oddawanie projektów akademickich
        </div>

        <h1 className="text-4xl sm:text-5xl font-extrabold text-white tracking-tight">
          System przesyłania i oceny prac <br />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-cyan-400">
            z kontrolą terminów i ról
          </span>
        </h1>

        <p className="max-w-2xl mx-auto text-slate-400 text-sm sm:text-base leading-relaxed">
          Platforma dedykowana studentom oraz prowadzącym Politechniki Śląskiej,
          gwarantująca walidację załączników, kontrolę dostępu (RBAC) oraz
          automatyczną blokadę po upływie deadline.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-8 text-left">
          <Link
            href="/student"
            className="group p-6 bg-slate-900/70 border border-slate-800/80 hover:border-indigo-500/60 rounded-2xl transition-all shadow-lg hover:shadow-indigo-500/5 flex flex-col justify-between"
          >
            <div className="space-y-3">
              <div className="w-12 h-12 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 group-hover:scale-105 transition-transform">
                <GraduationCap className="w-6 h-6" />
              </div>
              <h3 className="text-xl font-bold text-white group-hover:text-indigo-400 transition-colors">
                Panel Studenta
              </h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Przeglądaj przypisane zadania laboratoryjne i projektowe,
                przesyłaj pliki rozwiązań oraz sprawdzaj wystawione oceny i
                komentarze.
              </p>
            </div>
            <div className="mt-6 flex items-center gap-2 text-xs font-semibold text-indigo-400">
              Przejdź do widoku studenta
              <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
            </div>
          </Link>

          <Link
            href="/teacher"
            className="group p-6 bg-slate-900/70 border border-slate-800/80 hover:border-cyan-500/60 rounded-2xl transition-all shadow-lg hover:shadow-cyan-500/5 flex flex-col justify-between"
          >
            <div className="space-y-3">
              <div className="w-12 h-12 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400 group-hover:scale-105 transition-transform">
                <BookOpen className="w-6 h-6" />
              </div>
              <h3 className="text-xl font-bold text-white group-hover:text-cyan-400 transition-colors">
                Panel Prowadzącego
              </h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Twórz nowe zadania z terminem oddania (deadline), przeglądaj
                prace nadesłane przez grupy laboratoryjne i wystawiaj oceny.
              </p>
            </div>
            <div className="mt-6 flex items-center gap-2 text-xs font-semibold text-cyan-400">
              Przejdź do widoku prowadzącego
              <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
            </div>
          </Link>
        </div>
      </section>

      <footer className="border-t border-slate-800/60 py-6 text-center text-xs text-slate-500">
        HomeworkDrop &copy; {new Date().getFullYear()} &bull; Politechnika Śląska &bull; DevSecOps
      </footer>
    </main>
  );
}
