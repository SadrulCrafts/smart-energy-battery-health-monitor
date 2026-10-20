"use client";

/**
 * Dashboard.tsx
 * -------------
 * The whole overview page. It gets live data from useBatteryData() and hands
 * each part to its own component.
 */

import { useState } from "react";
import { useBatteryData } from "@/hooks/useBatteryData";
import { useNow } from "@/hooks/useNow";
import { setTheme, useTheme } from "@/hooks/useTheme";
import { phaseText, signed, SOURCE_LABEL, STATUS_STYLE } from "@/lib/format";
import { CHART_COLORS } from "@/lib/theme";
import BatteryCell from "./BatteryCell";
import CapacityPanel from "./CapacityPanel";
import Header from "./Header";
import MetricTile from "./MetricTile";
import ReadingsTable from "./ReadingsTable";
import Sidebar from "./Sidebar";
import SohPanel from "./SohPanel";
import StatusBanner from "./StatusBanner";
import VoltageChart from "./VoltageChart";

const DEVICE_KIND = {
  simulated: "Software simulator, not a physical cell",
  sensor: "INA219 and DS18B20 sensors on the test bench",
  nasa: "Historical NASA laboratory data",
} as const;

export default function Dashboard() {
  // null = follow the most recently active device; a key once the viewer picks one
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const { devices, activeKey, readings, latest, thresholds, modelInfo, health, totalStored, connection, error } =
    useBatteryData(selectedKey);
  const now = useNow();
  const theme = useTheme();

  const colors = CHART_COLORS[theme];
  const ageSeconds = latest && now > 0 ? Math.max(0, now - Date.parse(latest.timestamp) / 1000) : null;
  const status = latest?.status ?? "normal";
  const style = STATUS_STYLE[status];
  const alertCount = readings.filter((r) => r.status !== "normal").length;

  const warnV = thresholds?.voltage_low_warning_v ?? 3.2;
  const critV = thresholds?.voltage_low_critical_v ?? 3.0;
  const deviceLine = latest
    ? `Device ${latest.device_id ?? "unknown"}: ${DEVICE_KIND[latest.source].toLowerCase()}`
    : "Waiting for the first reading";

  const temperatures = readings.map((r) => r.temperature_c).filter((t): t is number => t !== null);
  const powers = readings.map((r) => Math.abs(r.voltage_v * r.current_a));

  return (
    <div id="top" className="grid min-h-screen grid-cols-[minmax(0,1fr)] lg:grid-cols-[256px_minmax(0,1fr)]">
      <Sidebar
        deviceId={latest?.device_id ?? null}
        deviceKind={latest ? DEVICE_KIND[latest.source] : null}
        apiVersion={health?.version ?? null}
        online={connection === "live" && ageSeconds !== null && ageSeconds <= 10}
        alertCount={alertCount}
      />

      <main className="flex w-full max-w-[1240px] min-w-0 flex-col gap-5 px-4 pt-7 pb-10 sm:px-6 lg:px-10">
        <Header
          source={latest?.source ?? null}
          deviceLine={deviceLine}
          connection={connection}
          ageSeconds={ageSeconds}
          theme={theme}
          onToggleTheme={() => setTheme(theme === "dark" ? "light" : "dark")}
          devices={devices}
          activeKey={activeKey}
          onSelectDevice={setSelectedKey}
        />

        <StatusBanner latest={latest} error={error} />

        <section
          id="voltage"
          aria-label="Live readings"
          className="relative flex scroll-mt-6 flex-wrap gap-x-11 gap-y-7 overflow-hidden rounded-3xl p-5 shadow-[var(--shadow)] sm:p-7"
          style={{
            border: "1px solid transparent",
            background:
              "linear-gradient(var(--panel-solid), var(--panel-solid)) padding-box, linear-gradient(135deg, rgba(59,108,255,0.7), rgba(47,212,240,0.3) 40%, var(--line) 70%) border-box",
          }}
        >
          <div
            aria-hidden="true"
            className="pointer-events-none absolute -top-40 -left-28 size-[460px] rounded-full"
            style={{ background: "radial-gradient(closest-side, var(--glow-a), transparent)" }}
          />

          <div className="relative flex max-w-[470px] flex-[1_1_420px] flex-wrap items-center gap-6">
            <BatteryCell voltage={latest?.voltage_v ?? null} status={status} warnBelowV={warnV} critBelowV={critV} />
            <div className="flex min-w-0 flex-col gap-4">
              <div>
                <div className="flex items-center gap-2 text-sm text-ink-2">
                  <span aria-hidden="true" className="h-[3px] w-3 rounded-sm bg-volt" />
                  Cell voltage
                </div>
                <div className="flex items-baseline gap-2">
                  <span className="font-display text-[52px] leading-[1.05] font-semibold tracking-tighter tabular-nums">
                    {latest ? latest.voltage_v.toFixed(3) : "–"}
                  </span>
                  <span className="font-display text-xl text-ink-2">V</span>
                </div>
              </div>
              {latest && (
                <span className={`inline-flex items-center gap-2 self-start rounded-full px-3 py-1.5 text-[13.5px] font-semibold ${style.chip}`}>
                  <span aria-hidden="true" className={`size-2 rounded-full ${style.dot}`} />
                  {style.label}
                </span>
              )}
              <p className="max-w-[28ch] text-sm text-ink-2">
                {latest ? `${phaseText(latest.current_a)}. ${SOURCE_LABEL[latest.source]}.` : "No reading yet."}
              </p>
            </div>
          </div>

          <div className="relative flex min-w-0 flex-[999_1_460px] flex-col gap-2.5">
            <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
              <h2 className="font-display text-[15px] font-medium">Voltage over time</h2>
              <span className="text-[13px] text-muted">Last {readings.length} readings</span>
            </div>
            <VoltageChart readings={readings} thresholds={thresholds} colors={colors} />
          </div>
        </section>

        <section aria-label="Measurements" className="grid grid-cols-[repeat(auto-fit,minmax(220px,1fr))] gap-4">
          <MetricTile
            label="Current"
            value={latest ? signed(latest.current_a, 3) : "–"}
            unit="A"
            note="Negative while discharging"
            color={colors.amp}
            trend={readings.map((r) => r.current_a)}
          />
          <MetricTile
            label="Temperature"
            value={latest?.temperature_c != null ? latest.temperature_c.toFixed(1) : "–"}
            unit="°C"
            note={
              thresholds
                ? `Warning at ${thresholds.temperature_high_warning_c} °C, critical at ${thresholds.temperature_high_critical_c} °C`
                : "Cell surface temperature"
            }
            color={colors.temp}
            trend={temperatures}
          />
          <MetricTile
            label="Power"
            value={latest ? Math.abs(latest.voltage_v * latest.current_a).toFixed(2) : "–"}
            unit="W"
            note="Voltage times current"
            color={colors.power}
            trend={powers}
          />
          <MetricTile
            label="Readings from this device"
            value={totalStored.toLocaleString("en-US")}
            unit=""
            note={`${alertCount} of the last ${readings.length} outside the limits`}
            color={colors.volt}
          />
        </section>

        <div className="flex flex-wrap items-stretch gap-5">
          <ReadingsTable readings={readings} />
          <SohPanel latest={latest} modelInfo={modelInfo} />
          <CapacityPanel source={latest?.source ?? null} deviceId={latest?.device_id ?? null} />
        </div>

        <footer id="limits" className="flex scroll-mt-6 flex-wrap justify-between gap-x-6 gap-y-2 text-[13px] text-muted">
          <span>
            Alert limits: warning below {warnV.toFixed(2)} V, critical below {critV.toFixed(2)} V.{" "}
            {thresholds?.note ?? "Demonstration values, not certified safety limits."}
          </span>
          <span>SoH model trained on the NASA PCoE Battery Data Set (Saha and Goebel, 2007).</span>
        </footer>
      </main>
    </div>
  );
}
