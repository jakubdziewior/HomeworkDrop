export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8 text-center">
      <div className="max-w-2xl bg-slate-900 border border-slate-800 rounded-2xl p-8 shadow-xl">
        <h1 className="text-3xl font-bold tracking-tight text-white mb-3">HomeworkDrop</h1>
        <p className="text-slate-400 text-sm mb-6">
          Bezpieczna platforma do przesyłania i weryfikacji projektów akademickich.
        </p>
        <div className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-500/10 border border-emerald-500/20 rounded-full text-emerald-400 text-sm font-medium">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
          System aktywny (Etap 2)
        </div>
      </div>
    </main>
  );
}
