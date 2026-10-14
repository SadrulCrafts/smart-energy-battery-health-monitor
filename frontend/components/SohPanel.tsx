"use client";

/**
 * SohPanel.tsx
 * ------------
 * State of health, shown honestly: live readings are never turned into an SoH
 * number. The button runs the model on one real NASA example so visitors can see
 * it working, with a note that this cell was part of the training data.
 */

import { useState } from "react";
import { api, NASA_EXAMPLE, type ModelInfo, type Reading, type SohPrediction } from "@/lib/api";

interface SohPanelProps {
  latest: Reading | null;
  modelInfo: ModelInfo | null;
}

export default function SohPanel({ latest, modelInfo }: SohPanelProps) {
  const [example, setExample] = useState<SohPrediction | null>(null);
  const [running, setRunning] = useState(false);
  const [exampleError, setExampleError] = useState<string | null>(null);

  const evaluated = latest?.soh_valid === true && latest.soh_pct !== null;
  const note =
    latest?.soh_note ??
    "One reading is not enough. The model needs the first 10 minutes of a 2 A discharge.";
  const mae = modelInfo?.lobo_overall_metrics?.mae;

  async function runExample() {
    if (example) {
      setExample(null);
      return;
    }
    setRunning(true);
    setExampleError(null);
    try {
      setExample(await api.predictSoh(NASA_EXAMPLE.features));
    } catch (e: unknown) {
      setExampleError(e instanceof Error ? e.message : String(e));
    } finally {
      setRunning(false);
    }
  }

  return (
    <section
      id="soh"
      aria-label="State of health"
      className="flex min-w-0 flex-[1_1_330px] scroll-mt-6 flex-col gap-4 rounded-[20px] border border-line bg-panel px-6 py-[22px] shadow-[var(--shadow)] backdrop-blur-md"
    >
      <h2 className="font-display text-[15px] font-medium">State of health</h2>

      <div className="flex items-center gap-4">
        <svg width="64" height="64" viewBox="0 0 92 92" aria-hidden="true" className="flex-none">
          <circle cx="46" cy="46" r="38" fill="none" stroke="var(--line-strong)" strokeWidth="8" strokeDasharray="4 7" strokeLinecap="round" />
          <path d="M28 46h9l4-8 6 16 4-8h13" fill="none" stroke="var(--muted)" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        {evaluated ? (
          <div className="font-display text-[28px] font-semibold tracking-tight">{latest!.soh_pct!.toFixed(1)} %</div>
        ) : (
          <div className="font-display text-xl font-medium whitespace-nowrap text-ink-2">Not evaluated</div>
        )}
      </div>
      <p className="-mt-1 text-sm text-ink-2">{note}</p>

      <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5 border-t border-line pt-3.5 text-sm">
        <dt className="text-muted">Model</dt>
        <dd>{modelInfo?.available ? "Random Forest" : (modelInfo?.problem ?? "Loading...")}</dd>
        <dt className="text-muted">Trained on</dt>
        <dd>NASA lab cells {modelInfo?.trained_on_cells.join(", ") || "B0005, B0006, B0007, B0018"}</dd>
        <dt className="text-muted">Error</dt>
        <dd>{mae === undefined ? "n/a" : `MAE ${mae.toFixed(1)} points on unseen NASA cells`}</dd>
      </dl>

      <button
        type="button"
        onClick={runExample}
        disabled={running || modelInfo?.available === false}
        className="min-h-11 cursor-pointer self-start rounded-xl border border-line-strong px-4 text-sm font-medium text-ink transition-colors hover:bg-hover disabled:cursor-not-allowed disabled:opacity-50"
      >
        {running ? "Running the model..." : example ? "Hide NASA example" : "Try the model on NASA data"}
      </button>

      {exampleError && <p className="text-sm text-crit-ink">{exampleError}</p>}

      {example && (
        <div
          className="flex flex-col gap-1 rounded-[14px] bg-active px-4 py-3.5 text-sm"
          style={{ boxShadow: "inset 0 0 0 1px var(--active-line)" }}
        >
          <div className="font-semibold">
            NASA cell {NASA_EXAMPLE.cell}, discharge {NASA_EXAMPLE.cycle}
          </div>
          {example.soh_pct === null ? (
            <div>{example.soh_note}</div>
          ) : (
            <div>
              Estimated {example.soh_pct.toFixed(1)} %, measured {NASA_EXAMPLE.measuredSohPct.toFixed(1)} %
            </div>
          )}
          <div className="text-[13px] text-ink-2">
            This cell was part of the training data, so this shows the model running, not its accuracy.
          </div>
        </div>
      )}
    </section>
  );
}
