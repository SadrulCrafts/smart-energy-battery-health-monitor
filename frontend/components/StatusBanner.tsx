/**
 * StatusBanner.tsx
 * ----------------
 * One line that says whether the latest reading is inside the alert limits.
 * The status and message come from the backend's alert service.
 */

import type { Reading } from "@/lib/api";
import { STATUS_STYLE } from "@/lib/format";

interface StatusBannerProps {
  latest: Reading | null;
  error: string | null;
}

function StatusIcon({ status }: { status: Reading["status"] }) {
  const common = {
    width: 18,
    height: 18,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 2.4,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true,
  };
  if (status === "normal") {
    return (
      <svg {...common}>
        <path d="m5 12.5 4.5 4.5L19 7.5" />
      </svg>
    );
  }
  if (status === "warning") {
    return (
      <svg {...common}>
        <path d="M12 7v6" />
        <path d="M12 17h.01" />
      </svg>
    );
  }
  return (
    <svg {...common}>
      <path d="M7 7l10 10M17 7 7 17" />
    </svg>
  );
}

export default function StatusBanner({ latest, error }: StatusBannerProps) {
  if (!latest) {
    return (
      <section
        aria-live="polite"
        className="flex flex-wrap items-center gap-x-4 gap-y-2 rounded-2xl border border-line bg-panel px-[18px] py-3.5"
      >
        {error ? (
          <span className="text-crit-ink">{error}</span>
        ) : (
          <span className="text-ink-2">
            No readings yet. Start the simulator with{" "}
            <code className="rounded-md bg-hover px-1.5 py-0.5 text-[13px] text-ink">python backend/simulator.py</code>
          </span>
        )}
      </section>
    );
  }

  const style = STATUS_STYLE[latest.status];
  const message = latest.alert_message ?? "All readings are inside the alert limits.";
  return (
    <section
      aria-live="polite"
      className={`flex flex-wrap items-center gap-x-4 gap-y-3 rounded-2xl border border-line px-[18px] py-3.5 ${style.banner}`}
    >
      <span
        className={`grid size-9 flex-none place-items-center rounded-full bg-panel-solid ${style.ink}`}
        style={{ boxShadow: `0 0 0 1px var(--line), 0 0 22px ${style.glow}` }}
      >
        <StatusIcon status={latest.status} />
      </span>
      <span className={`font-semibold ${style.ink}`}>{style.label}</span>
      <span className="min-w-0 flex-[1_1_320px]">{message}</span>
      <a href="#limits" className="text-sm">
        View alert limits
      </a>
    </section>
  );
}
