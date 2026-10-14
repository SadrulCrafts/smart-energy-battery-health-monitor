/**
 * ReadingsTable.tsx
 * -----------------
 * The newest readings, newest first, with the status the backend gave each one.
 */

import type { Reading } from "@/lib/api";
import { clock, signed, SOURCE_LABEL, STATUS_STYLE } from "@/lib/format";

const ROWS = 8;

export default function ReadingsTable({ readings }: { readings: Reading[] }) {
  const rows = readings.slice(-ROWS).reverse();
  const cell = "border-b border-line px-3 py-2.5 whitespace-nowrap";

  return (
    <section
      id="readings"
      aria-label="Recent readings"
      className="min-w-0 flex-[999_1_560px] scroll-mt-6 rounded-[20px] border border-line bg-panel px-6 pt-[22px] pb-3 shadow-[var(--shadow)] backdrop-blur-md"
    >
      <div className="mb-2 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <h2 className="font-display text-[15px] font-medium">Recent readings</h2>
        <span className="text-[13px] text-muted">Newest first</span>
      </div>
      {rows.length === 0 ? (
        <p className="py-6 text-sm text-muted">No readings stored yet.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[680px] border-collapse text-sm">
            <thead>
              <tr className="text-left text-muted">
                <th scope="col" className={`${cell} pl-0 font-medium`}>Time</th>
                <th scope="col" className={`${cell} font-medium`}>Status</th>
                <th scope="col" className={`${cell} text-right font-medium`}>Voltage</th>
                <th scope="col" className={`${cell} text-right font-medium`}>Current</th>
                <th scope="col" className={`${cell} text-right font-medium`}>Temp.</th>
                <th scope="col" className={`${cell} pr-0 font-medium`}>Message</th>
              </tr>
            </thead>
            <tbody className="tabular-nums">
              {rows.map((r) => {
                const style = STATUS_STYLE[r.status];
                return (
                  <tr key={r.id}>
                    <td className={`${cell} pl-0 text-ink-2`} title={SOURCE_LABEL[r.source]}>
                      {clock(r.timestamp)}
                    </td>
                    <td className={cell}>
                      <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[13px] font-medium ${style.chip}`}>
                        <span aria-hidden="true" className={`size-[7px] rounded-full ${style.dot}`} />
                        {style.label}
                      </span>
                    </td>
                    <td className={`${cell} text-right`}>{r.voltage_v.toFixed(3)} V</td>
                    <td className={`${cell} text-right`}>{signed(r.current_a, 3)} A</td>
                    <td className={`${cell} text-right`}>
                      {r.temperature_c === null ? "n/a" : `${r.temperature_c.toFixed(1)} °C`}
                    </td>
                    <td className={`${cell} pr-0 text-ink-2`}>
                      <div className="max-w-[240px] min-w-[160px] whitespace-normal">
                        {r.alert_message ?? "Inside limits"}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
