"use client";

/**
 * useBatteryData.ts
 * -----------------
 * Loads the recent readings once (REST) and then keeps them up to date with the
 * live WebSocket. If the connection drops, it reconnects every 3 seconds and
 * fills the gap from /history.
 */

import { useEffect, useState } from "react";
import {
  api,
  WS_URL,
  type Health,
  type LiveMessage,
  type ModelInfo,
  type Reading,
  type Thresholds,
} from "@/lib/api";

export type Connection = "connecting" | "live" | "offline";

const MAX_READINGS = 120;
const RECONNECT_MS = 3000;

/** Join two lists of readings, drop duplicates (same id), keep the newest MAX_READINGS. */
function merge(current: Reading[], incoming: Reading[]): Reading[] {
  const byId = new Map<number, Reading>();
  for (const reading of current) byId.set(reading.id, reading);
  for (const reading of incoming) byId.set(reading.id, reading);
  return [...byId.values()].sort((a, b) => a.id - b.id).slice(-MAX_READINGS);
}

export interface BatteryData {
  readings: Reading[];
  latest: Reading | null;
  thresholds: Thresholds | null;
  modelInfo: ModelInfo | null;
  health: Health | null;
  totalStored: number;
  connection: Connection;
  error: string | null;
}

export function useBatteryData(): BatteryData {
  const [readings, setReadings] = useState<Reading[]>([]);
  const [thresholds, setThresholds] = useState<Thresholds | null>(null);
  const [modelInfo, setModelInfo] = useState<ModelInfo | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [totalStored, setTotalStored] = useState(0);
  const [connection, setConnection] = useState<Connection>("connecting");
  const [error, setError] = useState<string | null>(null);

  // Things that rarely change: load once
  useEffect(() => {
    let cancelled = false;
    Promise.all([api.thresholds(), api.modelInfo(), api.health()])
      .then(([limits, model, status]) => {
        if (cancelled) return;
        setThresholds(limits);
        setModelInfo(model);
        setHealth(status);
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Readings: history on every (re)connect, then live messages
  useEffect(() => {
    let socket: WebSocket | null = null;
    let retryTimer: ReturnType<typeof setTimeout> | undefined;
    let stopped = false;

    const loadHistory = () => {
      Promise.all([api.history(MAX_READINGS), api.status()])
        .then(([history, status]) => {
          if (stopped) return;
          setReadings((current) => merge(current, history));
          setTotalStored(status.total_readings);
          setError(null);
        })
        .catch((e: unknown) => {
          if (!stopped) setError(e instanceof Error ? e.message : String(e));
        });
    };

    const connect = () => {
      socket = new WebSocket(WS_URL);
      socket.onopen = () => {
        setConnection("live");
        loadHistory();
      };
      socket.onmessage = (event: MessageEvent<string>) => {
        const message = JSON.parse(event.data) as LiveMessage;
        if (message.type !== "reading") return;
        setReadings((current) => merge(current, [message.data]));
        setTotalStored((count) => count + 1);
      };
      socket.onclose = () => {
        if (stopped) return;
        setConnection("offline");
        retryTimer = setTimeout(connect, RECONNECT_MS);
      };
    };

    loadHistory();
    connect();
    return () => {
      stopped = true;
      clearTimeout(retryTimer);
      socket?.close();
    };
  }, []);

  return {
    readings,
    latest: readings.length > 0 ? readings[readings.length - 1] : null,
    thresholds,
    modelInfo,
    health,
    totalStored,
    connection,
    error,
  };
}
