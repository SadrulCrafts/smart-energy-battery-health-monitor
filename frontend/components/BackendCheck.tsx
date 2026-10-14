"use client";

/**
 * BackendCheck.tsx
 * ----------------
 * Temporary test panel: proves the dashboard can reach the backend
 * (REST via /health) and receive live readings (WebSocket /ws).
 * It will be removed once the real dashboard is built.
 */

import { useEffect, useState } from "react";
import { api, API_URL, WS_URL, type Health, type LiveMessage } from "@/lib/api";

type SocketState = "connecting" | "open" | "closed";

export default function BackendCheck() {
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [socket, setSocket] = useState<SocketState>("connecting");
  const [liveCount, setLiveCount] = useState(0);
  const [lastVoltage, setLastVoltage] = useState<number | null>(null);

  // 1) REST: ask the backend once if it is healthy
  useEffect(() => {
    api
      .health()
      .then(setHealth)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : String(e)));
  }, []);

  // 2) WebSocket: listen for readings pushed by the backend
  useEffect(() => {
    const ws = new WebSocket(WS_URL);
    ws.onopen = () => setSocket("open");
    ws.onclose = () => setSocket("closed");
    ws.onmessage = (event) => {
      const message = JSON.parse(event.data) as LiveMessage;
      if (message.type === "reading") {
        setLiveCount((count) => count + 1);
        setLastVoltage(message.data.voltage_v);
      }
    };
    return () => ws.close();
  }, []);

  const rows: [string, string, boolean][] = [
    ["Backend", error ?? (health ? `${health.status}, version ${health.version}` : "checking..."), !error && health?.status === "ok"],
    ["Database", health?.database ?? "-", health?.database === "ok"],
    ["SoH model", health?.soh_model ?? "-", health?.soh_model === "loaded"],
    ["Live connection", socket, socket === "open"],
    ["Live readings received", lastVoltage === null ? String(liveCount) : `${liveCount} (last ${lastVoltage.toFixed(3)} V)`, liveCount > 0],
  ];

  return (
    <section className="rounded-2xl border border-line bg-panel p-5 backdrop-blur">
      <h2 className="font-display text-base font-medium">Backend connection check</h2>
      <p className="mt-1 text-sm text-muted">API address: {API_URL}</p>
      <dl className="mt-4 grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 text-sm">
        {rows.map(([label, value, ok]) => (
          <div key={label} className="contents">
            <dt className="text-ink-2">{label}</dt>
            <dd className={ok ? "text-good-ink" : "text-ink"}>{value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}