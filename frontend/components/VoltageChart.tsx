"use client";

/**
 * VoltageChart.tsx
 * ----------------
 * Voltage of the recent readings, with the alert zones drawn as shaded bands.
 * Hover (or tap) the chart to see the exact value and time of a reading.
 */

import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Reading, Thresholds } from "@/lib/api";
import { clock } from "@/lib/format";
import type { ChartColors } from "@/lib/theme";

const GAP_MS = 30_000;

interface VoltageChartProps {
  readings: Reading[];
  thresholds: Thresholds | null;
  colors: ChartColors;
}

export default function VoltageChart({ readings, thresholds, colors }: VoltageChartProps) {
  if (readings.length < 2) {
    return (
      <div className="grid h-[280px] place-items-center rounded-xl border border-dashed border-line text-sm text-muted">
        Waiting for readings to draw the chart
      </div>
    );
  }

  // A pause longer than GAP_MS (simulator stopped, backend restarted) breaks the line,
  // so the chart never draws a value for a time when nothing was measured.
  const data: { t: number; v: number | null }[] = [];
  let gaps = 0;
  readings.forEach((r, i) => {
    const t = Date.parse(r.timestamp);
    if (i > 0) {
      const previous = Date.parse(readings[i - 1].timestamp);
      if (t - previous > GAP_MS) {
        data.push({ t: previous + 1, v: null });
        gaps += 1;
      }
    }
    data.push({ t, v: r.voltage_v });
  });
  const values = readings.map((r) => r.voltage_v);
  const low = Math.min(2.8, ...values);
  const high = Math.max(4.3, ...values);

  const warnLow = thresholds?.voltage_low_warning_v ?? 3.2;
  const critLow = thresholds?.voltage_low_critical_v ?? 3.0;
  const warnHigh = thresholds?.voltage_high_warning_v ?? 4.22;
  const critHigh = thresholds?.voltage_high_critical_v ?? 4.25;
  const tick = { fill: colors.muted, fontSize: 12 };

  return (
    <div className="w-full">
      <div className="h-[280px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
            <defs>
              <linearGradient id="voltFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={colors.volt} stopOpacity={0.32} />
                <stop offset="100%" stopColor={colors.volt} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid vertical={false} stroke={colors.grid} />
            <ReferenceArea y1={critHigh} y2={high} fill={colors.critBand} fillOpacity={1} ifOverflow="hidden" />
            <ReferenceArea y1={warnHigh} y2={critHigh} fill={colors.warnBand} fillOpacity={1} ifOverflow="hidden" />
            <ReferenceArea
              y1={critLow}
              y2={warnLow}
              fill={colors.warnBand}
              fillOpacity={1}
              ifOverflow="hidden"
              label={{ value: `Warning below ${warnLow.toFixed(2)} V`, position: "insideRight", fill: colors.warnInk, fontSize: 12 }}
            />
            <ReferenceArea
              y1={low}
              y2={critLow}
              fill={colors.critBand}
              fillOpacity={1}
              ifOverflow="hidden"
              label={{ value: `Critical below ${critLow.toFixed(2)} V`, position: "insideRight", fill: colors.critInk, fontSize: 12 }}
            />
            <XAxis
              dataKey="t"
              type="number"
              scale="time"
              domain={["dataMin", "dataMax"]}
              tickFormatter={(value: number) => clock(value)}
              tick={tick}
              tickLine={false}
              axisLine={{ stroke: colors.axis }}
              minTickGap={56}
            />
            <YAxis
              domain={[low, high]}
              ticks={[3.0, 3.2, 3.6, 4.0, 4.2]}
              tickFormatter={(value: number) => value.toFixed(1)}
              tick={tick}
              tickLine={false}
              axisLine={false}
              width={34}
            />
            <Tooltip
              cursor={{ stroke: colors.axis, strokeWidth: 1 }}
              content={({ active, payload }) => {
                if (!active || !payload || payload.length === 0) return null;
                const point = payload[0].payload as { t: number; v: number | null };
                if (point.v === null) return null;
                return (
                  <div className="rounded-xl border border-line bg-panel-solid px-3 py-2 text-sm shadow-lg">
                    <div className="text-muted">{clock(point.t)}</div>
                    <div className="font-semibold text-ink tabular-nums">{point.v.toFixed(3)} V</div>
                  </div>
                );
              }}
            />
            <Area
              type="monotone"
              dataKey="v"
              stroke={colors.volt}
              strokeWidth={2.25}
              fill="url(#voltFill)"
              baseValue={low}
              dot={false}
              activeDot={{ r: 5, stroke: colors.panel, strokeWidth: 2, fill: colors.volt }}
              connectNulls={false}
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
      {gaps > 0 && (
        <p className="mt-1 text-xs text-muted">
          Breaks in the line are pauses with no readings ({gaps} in view).
        </p>
      )}
    </div>
  );
}
