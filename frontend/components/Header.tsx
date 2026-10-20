/**
 * Header.tsx
 * ----------
 * Page title, the data-source label, the live connection state and the theme switch.
 */

import type { Device, Source } from "@/lib/api";
import { ageText, SOURCE_LABEL } from "@/lib/format";
import { keyOf, type Connection } from "@/hooks/useBatteryData";
import type { Theme } from "@/lib/theme";

interface HeaderProps {
  source: Source | null;
  deviceLine: string;
  connection: Connection;
  ageSeconds: number | null;
  theme: Theme;
  onToggleTheme: () => void;
  devices: Device[];
  activeKey: string | null;
  onSelectDevice: (key: string) => void;
}

function SourceChip({ source }: { source: Source }) {
  const base = "inline-flex min-h-9 items-center rounded-full px-3.5 text-[13.5px]";
  if (source === "simulated") {
    return (
      <span
        className={`${base} border border-line-strong font-medium`}
        style={{ background: "repeating-linear-gradient(135deg, var(--hatch) 0 2px, transparent 2px 7px)" }}
      >
        {SOURCE_LABEL.simulated}
      </span>
    );
  }
  if (source === "sensor") {
    return <span className={`${base} bg-ink font-semibold text-bg`}>{SOURCE_LABEL.sensor}</span>;
  }
  return <span className={`${base} border-[1.5px] border-ion font-medium text-ink`}>{SOURCE_LABEL.nasa}</span>;
}

const SOURCE_SHORT: Record<Source, string> = { simulated: "simulated", sensor: "sensor", nasa: "NASA" };

function DevicePicker({
  devices,
  activeKey,
  onSelect,
}: {
  devices: Device[];
  activeKey: string | null;
  onSelect: (key: string) => void;
}) {
  return (
    <label className="inline-flex min-h-9 items-center gap-2 rounded-full border border-line bg-panel pr-2 pl-3.5 text-[13.5px] text-ink-2">
      Device
      <select
        value={activeKey ?? ""}
        onChange={(event) => onSelect(event.target.value)}
        className="cursor-pointer rounded-md bg-transparent py-1 font-medium text-ink outline-none"
      >
        {devices.map((device) => {
          const key = keyOf(device.source, device.device_id);
          return (
            <option key={key} value={key}>
              {device.device_id ?? "unknown"} ({SOURCE_SHORT[device.source]})
            </option>
          );
        })}
      </select>
    </label>
  );
}

function LivePill({ connection, ageSeconds }: { connection: Connection; ageSeconds: number | null }) {
  let dot = "bg-muted";
  let text = "Connecting...";
  if (connection === "offline") {
    dot = "bg-crit";
    text = "Offline, reconnecting";
  } else if (connection === "live" && ageSeconds === null) {
    dot = "bg-muted";
    text = "Connected, waiting for readings";
  } else if (connection === "live" && ageSeconds !== null && ageSeconds <= 10) {
    dot = "bg-good animate-live";
    text = `Live, updated ${ageText(ageSeconds)}`;
  } else if (connection === "live" && ageSeconds !== null) {
    dot = "bg-warn";
    text = `Connected, last reading ${ageText(ageSeconds)}`;
  }
  return (
    <span className="inline-flex min-h-9 items-center gap-2 rounded-full border border-line bg-panel px-3.5 text-[13.5px] text-ink-2">
      <span aria-hidden="true" className={`size-2 rounded-full ${dot}`} />
      {text}
    </span>
  );
}

export default function Header({
  source,
  deviceLine,
  connection,
  ageSeconds,
  theme,
  onToggleTheme,
  devices,
  activeKey,
  onSelectDevice,
}: HeaderProps) {
  const next = theme === "dark" ? "Light theme" : "Dark theme";
  return (
    <header className="flex flex-wrap items-center justify-between gap-x-5 gap-y-3.5">
      <div className="min-w-0">
        <h1 className="font-display text-[26px] font-semibold tracking-tight">Overview</h1>
        <p className="mt-0.5 text-sm text-ink-2">{deviceLine}</p>
      </div>
      <div className="flex flex-wrap items-center gap-2.5">
        {devices.length > 1 && <DevicePicker devices={devices} activeKey={activeKey} onSelect={onSelectDevice} />}
        {source && <SourceChip source={source} />}
        <LivePill connection={connection} ageSeconds={ageSeconds} />
        <button
          type="button"
          onClick={onToggleTheme}
          className="inline-flex min-h-11 cursor-pointer items-center gap-2 rounded-xl border border-line bg-panel px-3.5 text-sm text-ink transition-colors hover:border-line-strong hover:bg-hover"
        >
          {theme === "dark" ? (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <circle cx="12" cy="12" r="4" />
              <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
            </svg>
          ) : (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />
            </svg>
          )}
          {next}
        </button>
      </div>
    </header>
  );
}
