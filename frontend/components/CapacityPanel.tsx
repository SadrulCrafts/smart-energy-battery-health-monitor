"use client";

/**
 * CapacityPanel.tsx
 * -----------------
 * MEASURED capacity of the cell on the test bench: the current added up over each
 * discharge (coulomb counting, done by the backend in GET /capacity). This is a
 * measurement, not a model estimate, and the panel always says what limits it:
 * a run that did not start full or stopped early gets no State of Health.
 */

import { useEffect, useState } from "react";
import { api, type Capacity, type DischargeRun, type Source } from "@/lib/api";
import { durationText } from "@/lib/format";

const REFRESH_MS = 10_000;

const ENDED: Record<DischargeRun["ended"], { label: string; chip: string }> = {
  cutoff: { label: "Reached cut-off", chip: "bg-good-bg text-good-ink" },
  stopped_early: { label: "Stopped early", chip: "bg-warn-bg text-warn-ink" },
  data_gap: { label: "Readings interrupted", chip: "bg-warn-bg text-warn-ink" },
  in_progress: { label: "Discharging now", chip: "bg-active text-ink" },
};

interface CapacityPanelProps {
  source: Source | null;
  deviceId: string | null;
}

export default function CapacityPanel({ source, deviceId }: CapacityPanelProps) {
  const [capacity, setCapacity] = useState<Capacity | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (source === null) return;
    let cancelled = false;
    const load = () => {
      api
        .capacity(source, deviceId)
        .then((result) => {
          if (!cancelled) {
            setCapacity(result);
            setError(null);
          }
        })
        .catch((e: unknown) => {
          if (!cancelled) setError(e instanceof Error ? e.message : String(e));
        });
    };
    load();
    const timer = setInterval(load, REFRESH_MS);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [source, deviceId]);

  // Ignore an answer that belongs to a device the viewer has switched away from
  const current = capacity && capacity.source === source && capacity.device_id === deviceId ? capacity : null;
  const latest = current?.runs[0] ?? null;
  const earlier = current?.runs.slice(1, 4) ?? [];

  return (
    <section
      id="capacity"
      aria-label="Measured capacity"
      className="flex min-w-0 flex-[1_1_100%] scroll-mt-6 flex-col gap-4 rounded-[20px] border border-line bg-panel px-6 py-[22px] shadow-[var(--shadow)] backdrop-blur-md"
    >
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <h2 className="font-display text-[15px] font-medium">Measured capacity</h2>
        <span className="text-[13px] text-muted">Coulomb counting on sensor data, not a model</span>
      </div>

      {error && <p className="text-sm text-crit-ink">{error}</p>}

      {!current || !current.available ? (
        <p className="max-w-[70ch] text-sm text-ink-2">
          {current?.note ?? (source === null ? "Waiting for the first reading." : "Loading...")}
        </p>
      ) : latest === null ? (
        <p className="max-w-[70ch] text-sm text-ink-2">
          {current.note} Start a discharge on the test bench: the firmware connects the load and
          this panel measures how much charge the cell delivers down to {current.cutoff_v.toFixed(2)} V.
        </p>
      ) : (
        <div className="flex flex-wrap gap-x-10 gap-y-5">
          <div className="flex min-w-0 flex-[1_1_260px] flex-col gap-3">
            <span className={`inline-flex self-start rounded-full px-3 py-1 text-[13px] font-semibold ${ENDED[latest.ended].chip}`}>
              {ENDED[latest.ended].label}
            </span>
            <div className="flex items-baseline gap-2">
              <span className="font-display text-[44px] leading-none font-semibold tracking-tighter tabular-nums">
                {Math.round(latest.capacity_mah).toLocaleString("en-US")}
              </span>
              <span className="font-display text-lg text-ink-2">mAh{latest.ended === "in_progress" ? " so far" : ""}</span>
            </div>
            <div className="text-sm">
              {latest.soh_pct !== null ? (
                <span>
                  Measured State of Health{" "}
                  <span className="font-display font-semibold">{latest.soh_pct.toFixed(1)} %</span> of the rated{" "}
                  {current.rated_capacity_mah.toLocaleString("en-US")} mAh
                </span>
              ) : (
                <span className="font-medium text-ink-2">State of Health not evaluated for this run</span>
              )}
            </div>
            <p className="max-w-[56ch] text-[13px] text-ink-2">{latest.soh_note}</p>
            {latest.warnings.map((w) => (
              <p key={w} className="text-[13px] text-warn-ink">
                {w}
              </p>
            ))}
          </div>

          <dl className="grid min-w-0 flex-[1_1_280px] grid-cols-[auto_1fr] content-start gap-x-5 gap-y-1.5 text-sm">
            <dt className="text-muted">Started at</dt>
            <dd className="tabular-nums">
              {latest.rest_voltage_v !== null ? `${latest.rest_voltage_v.toFixed(3)} V at rest` : "unknown"}
              {latest.started_full ? " (full)" : ""}
            </dd>
            <dt className="text-muted">Ended at</dt>
            <dd className="tabular-nums">{latest.end_voltage_v.toFixed(3)} V under load</dd>
            <dt className="text-muted">Duration</dt>
            <dd className="tabular-nums">{durationText(latest.duration_s)}</dd>
            <dt className="text-muted">Mean current</dt>
            <dd className="tabular-nums">{latest.mean_current_a.toFixed(3)} A</dd>
            <dt className="text-muted">Energy</dt>
            <dd className="tabular-nums">{latest.energy_wh.toFixed(2)} Wh</dd>
            <dt className="text-muted">Temperature</dt>
            <dd className="tabular-nums">
              {latest.max_temperature_c !== null
                ? `max ${latest.max_temperature_c.toFixed(1)} °C (rise ${latest.temperature_rise_c?.toFixed(1)} °C)`
                : "no readings"}
            </dd>
          </dl>

          {earlier.length > 0 && (
            <div className="flex min-w-0 flex-[1_1_100%] flex-col gap-1.5 border-t border-line pt-3.5 text-sm">
              <div className="text-muted">Earlier runs</div>
              {earlier.map((run) => (
                <div key={run.start} className="flex flex-wrap gap-x-4 tabular-nums">
                  <span className="text-ink-2">{new Date(run.start).toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short" })}</span>
                  <span>{Math.round(run.capacity_mah).toLocaleString("en-US")} mAh</span>
                  <span className="text-ink-2">{ENDED[run.ended].label}</span>
                  {run.soh_pct !== null && <span>SoH {run.soh_pct.toFixed(1)} %</span>}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </section>
  );
}
