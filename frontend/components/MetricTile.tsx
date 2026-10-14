"use client";

/**
 * MetricTile.tsx
 * --------------
 * One measured or derived quantity: label, current value and a small trend line.
 */

import { Area, AreaChart, ResponsiveContainer, YAxis } from "recharts";

interface MetricTileProps {
  label: string;
  value: string;
  unit: string;
  note: string;
  color: string;
  trend?: number[];
}

export default function MetricTile({ label, value, unit, note, color, trend }: MetricTileProps) {
  const points = (trend ?? []).map((y, x) => ({ x, y }));
  return (
    <div className="flex min-w-0 flex-col gap-1.5 rounded-[20px] border border-line bg-panel px-[18px] pt-[18px] pb-3.5 shadow-[var(--shadow)] backdrop-blur-md transition-[border-color,transform] duration-200 hover:-translate-y-0.5 hover:border-line-strong motion-reduce:hover:translate-y-0">
      <div className="flex items-center gap-2 text-sm text-ink-2">
        <span aria-hidden="true" className="h-[3px] w-3 rounded-sm" style={{ background: color }} />
        {label}
      </div>
      <div className="flex items-baseline gap-1.5">
        <span className="font-display text-[26px] font-semibold tracking-tight tabular-nums">{value}</span>
        <span className="text-sm text-ink-2">{unit}</span>
      </div>
      <div className="text-[12.5px] text-muted">{note}</div>
      {points.length > 1 ? (
        <div className="mt-1.5 h-[46px]" aria-hidden="true">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={points} margin={{ top: 4, right: 0, bottom: 0, left: 0 }}>
              <YAxis hide domain={["auto", "auto"]} />
              <Area
                type="monotone"
                dataKey="y"
                stroke={color}
                strokeWidth={2}
                fill={color}
                fillOpacity={0.12}
                dot={false}
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="mt-1.5 h-[46px]" aria-hidden="true" />
      )}
    </div>
  );
}
