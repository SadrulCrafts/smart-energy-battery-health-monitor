import BackendCheck from "@/components/BackendCheck";

export default function Home() {
  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col justify-center gap-8 p-8">
      <div className="flex items-center gap-4">
        <div className="grid size-14 place-items-center rounded-2xl bg-linear-135 from-cobalt to-ion shadow-[0_10px_30px_-8px_rgba(59,108,255,0.7)]">
          <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <rect x="7" y="4" width="10" height="17" rx="3" />
            <path d="M10.5 2h3" />
            <path d="M2 13h5.5l1.8-3.5 2.7 7 2-4.5H22" />
          </svg>
        </div>
        <div className="leading-tight">
          <p className="font-display text-2xl font-semibold tracking-tight">Battery Health</p>
          <p className="font-display text-lg text-ink-2">Monitor</p>
        </div>
      </div>

      <BackendCheck />
    </main>
  );
}