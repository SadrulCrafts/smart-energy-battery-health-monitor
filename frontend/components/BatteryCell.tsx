/**
 * BatteryCell.tsx
 * ---------------
 * The glass 18650 cell graphic. The fill level shows where the VOLTAGE sits on a
 * 2.8 to 4.3 V scale (it is not state of charge). Shaded zones are the alert limits.
 */

import type { Status } from "@/lib/api";

const V_MIN = 2.8;
const V_MAX = 4.3;

const FILLS: Record<Status, { fill: string; glow: string; rim: string }> = {
  normal: {
    fill: "linear-gradient(0deg, #2f55e6, #3b6cff 45%, #2fd4f0)",
    glow: "radial-gradient(closest-side, rgba(59, 108, 255, 0.9), rgba(47, 212, 240, 0))",
    rim: "rgba(47, 212, 240, 0.55)",
  },
  warning: {
    fill: "linear-gradient(0deg, #c97800, #fab219 55%, #ffd36b)",
    glow: "radial-gradient(closest-side, rgba(250, 178, 25, 0.85), rgba(250, 178, 25, 0))",
    rim: "rgba(255, 211, 107, 0.55)",
  },
  critical: {
    fill: "linear-gradient(0deg, #a81f1f, #e05252 55%, #ff8a8a)",
    glow: "radial-gradient(closest-side, rgba(224, 82, 82, 0.9), rgba(224, 82, 82, 0))",
    rim: "rgba(255, 138, 138, 0.55)",
  },
};

function percent(volts: number): number {
  return Math.min(Math.max((volts - V_MIN) / (V_MAX - V_MIN), 0), 1) * 100;
}

interface BatteryCellProps {
  voltage: number | null;
  status: Status;
  warnBelowV: number;
  critBelowV: number;
  height?: number;
}

export default function BatteryCell({ voltage, status, warnBelowV, critBelowV, height = 300 }: BatteryCellProps) {
  const bodyWidth = Math.round(height * 0.44);
  const innerHeight = height - 14 - 12; // cap overlap + padding
  const look = FILLS[status];
  const fillPct = voltage === null ? 0 : percent(voltage);
  const ticks = [4.2, warnBelowV, critBelowV];

  return (
    <div
      role="img"
      aria-label={
        voltage === null
          ? "Cell graphic, no reading yet"
          : `Cell voltage ${voltage.toFixed(3)} V on a 2.8 to 4.3 V scale, status ${status}`
      }
      className="flex flex-none items-stretch gap-3"
      style={{ width: bodyWidth + 64, height }}
    >
      <div className="relative h-full flex-none" style={{ width: bodyWidth }}>
        <div
          aria-hidden="true"
          className="absolute -inset-x-6 top-[18%] bottom-0 rounded-full opacity-55 blur-[38px]"
          style={{ background: look.glow }}
        />
        <div
          aria-hidden="true"
          className="absolute top-0 right-[32%] left-[32%] h-4 rounded-t-md rounded-b-sm"
          style={{ background: "linear-gradient(90deg, #7b879c, #eef2f8 45%, #8b97ad)" }}
        />
        <div
          className="absolute inset-x-0 top-3.5 bottom-0 rounded-[26px] border border-line-strong p-1.5"
          style={{
            background: "linear-gradient(160deg, rgba(255, 255, 255, 0.20), rgba(255, 255, 255, 0.03))",
            boxShadow: "inset 0 1px 0 rgba(255, 255, 255, 0.22), 0 18px 40px -18px rgba(0, 0, 0, 0.55)",
          }}
        >
          <div className="relative h-full overflow-hidden rounded-[20px]" style={{ background: "var(--track)" }}>
            <div
              aria-hidden="true"
              className="absolute inset-x-0 bottom-0"
              style={{ height: `${percent(critBelowV)}%`, background: "var(--crit-band)" }}
            />
            <div
              aria-hidden="true"
              className="absolute inset-x-0"
              style={{
                bottom: `${percent(critBelowV)}%`,
                height: `${percent(warnBelowV) - percent(critBelowV)}%`,
                background: "var(--warn-band)",
              }}
            />
            <div
              className="absolute inset-x-0 bottom-0 overflow-hidden transition-[height] duration-700 ease-out"
              style={{ height: `${fillPct}%`, background: look.fill, boxShadow: `0 -6px 24px ${look.rim}` }}
            >
              <div
                aria-hidden="true"
                className="animate-shimmer absolute inset-0"
                style={{ background: "linear-gradient(180deg, rgba(255,255,255,0), rgba(255,255,255,0.30), rgba(255,255,255,0))" }}
              />
              <div aria-hidden="true" className="absolute inset-x-0 top-0 h-0.5 bg-white/85" />
            </div>
            {ticks.map((volts) => (
              <div
                key={volts}
                aria-hidden="true"
                className="absolute inset-x-0 border-t border-dashed border-white/45"
                style={{ bottom: `${percent(volts)}%` }}
              />
            ))}
          </div>
          <div
            aria-hidden="true"
            className="absolute top-5 bottom-5 left-3.5 w-[9px] rounded-md"
            style={{ background: "linear-gradient(180deg, rgba(255,255,255,0.45), rgba(255,255,255,0))" }}
          />
        </div>
      </div>
      <div className="relative h-full flex-1">
        {ticks.map((volts) => (
          <span
            key={volts}
            className="absolute left-0 text-xs leading-4 whitespace-nowrap text-muted tabular-nums"
            style={{ bottom: Math.round(6 + (percent(volts) / 100) * innerHeight - 8) }}
          >
            {volts.toFixed(1)} V
          </span>
        ))}
      </div>
    </div>
  );
}
