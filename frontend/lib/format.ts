/**
 * format.ts
 * ---------
 * Small helpers that turn raw numbers and codes into text and styles for the UI.
 */

import type { Source, Status } from "./api";

/** Number with a real minus sign (−0.381 instead of -0.381). */
export function signed(value: number, digits: number): string {
  const text = Math.abs(value).toFixed(digits);
  return value < 0 ? `−${text}` : text;
}

/** "14:32:10" in 24-hour time. */
export function clock(value: string | number): string {
  return new Date(value).toLocaleTimeString("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

/** "just now", "12 s ago", "3 min ago", "2 h ago". */
export function ageText(seconds: number): string {
  if (seconds < 2) return "just now";
  if (seconds < 60) return `${Math.round(seconds)} s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)} min ago`;
  return `${Math.floor(seconds / 3600)} h ago`;
}

/** What the cell is doing, from the sign of the current. */
export function phaseText(currentA: number): string {
  if (currentA < -0.05) return "Discharging";
  if (currentA > 0.05) return "Charging";
  return "Resting, no current";
}

export const SOURCE_LABEL: Record<Source, string> = {
  simulated: "Simulated data",
  sensor: "Sensor data",
  nasa: "NASA lab data",
};

/** Tailwind classes per status. Status colors are never used for anything else. */
export const STATUS_STYLE: Record<
  Status,
  { label: string; chip: string; dot: string; ink: string; banner: string; glow: string }
> = {
  normal: {
    label: "Normal",
    chip: "bg-good-bg text-good-ink",
    dot: "bg-good",
    ink: "text-good-ink",
    banner: "bg-good-bg",
    glow: "rgba(12, 163, 12, 0.45)",
  },
  warning: {
    label: "Warning",
    chip: "bg-warn-bg text-warn-ink",
    dot: "bg-warn",
    ink: "text-warn-ink",
    banner: "bg-warn-bg",
    glow: "rgba(250, 178, 25, 0.45)",
  },
  critical: {
    label: "Critical",
    chip: "bg-crit-bg text-crit-ink",
    dot: "bg-crit",
    ink: "text-crit-ink",
    banner: "bg-crit-bg",
    glow: "rgba(224, 82, 82, 0.5)",
  },
};

/** "4 h 12 min", "12 min 5 s", "45 s". */
export function durationText(seconds: number): string {
  const s = Math.round(seconds);
  if (s < 60) return `${s} s`;
  if (s < 3600) return `${Math.floor(s / 60)} min ${s % 60} s`;
  return `${Math.floor(s / 3600)} h ${Math.floor((s % 3600) / 60)} min`;
}
