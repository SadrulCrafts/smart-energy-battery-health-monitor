"use client";

/**
 * useBatteryData.ts
 * -----------------
 * Keeps the dashboard's data up to date for ONE device at a time.
 *
 * - /devices lists every device that has sent readings. Unless the viewer picks
 *   one, the most recently active device is shown.
 * - /history loads that device's recent readings; the WebSocket adds new ones.
 *   Readings are kept per device, so switching is instant and devices never mix.
 * - If the connection drops, it reconnects every 3 seconds and fills the gap.
 */

import { useEffect, useMemo, useState } from "react";
import {
  api,
  WS_URL,
  type Device,
  type Health,
  type LiveMessage,
  type ModelInfo,
  type Reading,
  type Source,
  type Thresholds,
} from "@/lib/api";

export type Connection = "connecting" | "live" | "offline";
export interface DeviceKey {
  source: Source;
  deviceId: string | null;
}

const MAX_READINGS = 120;
const RECONNECT_MS = 3000;

/** A stable text key for one device, e.g. '["sensor","arduino-uno-1"]'. */
export function keyOf(source: Source, deviceId: string | null): string {
  return JSON.stringify([source, deviceId]);
}

export function parseKey(key: string): DeviceKey {
  const [source, deviceId] = JSON.parse(key) as [Source, string | null];
  return { source, deviceId };
}

/** Join two lists of readings, drop duplicates (same id), keep the newest MAX_READINGS. */
function merge(current: Reading[], incoming: Reading[]): Reading[] {
  const byId = new Map<number, Reading>();
  for (const reading of current) byId.set(reading.id, reading);
  for (const reading of incoming) byId.set(reading.id, reading);
  return [...byId.values()].sort((a, b) => a.id - b.id).slice(-MAX_READINGS);
}

/** Add or update the device of a new reading and keep the list newest first. */
function upsertDevice(devices: Device[], reading: Reading): Device[] {
  const key = keyOf(reading.source, reading.device_id);
  const existing = devices.find((d) => keyOf(d.source, d.device_id) === key);
  const updated: Device = {
    source: reading.source,
    device_id: reading.device_id,
    readings: (existing?.readings ?? 0) + 1,
    last_seen: reading.timestamp,
    last_status: reading.status,
  };
  const others = devices.filter((d) => keyOf(d.source, d.device_id) !== key);
  return [updated, ...others].sort((a, b) => Date.parse(b.last_seen) - Date.parse(a.last_seen));
}

export interface BatteryData {
  devices: Device[];
  activeKey: string | null;
  readings: Reading[];
  latest: Reading | null;
  totalStored: number;
  thresholds: Thresholds | null;
  modelInfo: ModelInfo | null;
  health: Health | null;
  connection: Connection;
  error: string | null;
}

export function useBatteryData(selectedKey: string | null): BatteryData {
  const [devices, setDevices] = useState<Device[]>([]);
  const [readingsByKey, setReadingsByKey] = useState<Record<string, Reading[]>>({});
  const [thresholds, setThresholds] = useState<Thresholds | null>(null);
  const [modelInfo, setModelInfo] = useState<ModelInfo | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [connection, setConnection] = useState<Connection>("connecting");
  const [connectedAt, setConnectedAt] = useState(0);   // changes on every (re)connect
  const [error, setError] = useState<string | null>(null);

  // The viewer's choice, or else the most recently active device
  const activeKey =
    selectedKey ?? (devices.length > 0 ? keyOf(devices[0].source, devices[0].device_id) : null);

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

  // Live connection: device list on every (re)connect, then each new reading
  useEffect(() => {
    let socket: WebSocket | null = null;
    let retryTimer: ReturnType<typeof setTimeout> | undefined;
    let stopped = false;

    const loadDevices = () => {
      api
        .devices()
        .then((list) => {
          if (!stopped) {
            setDevices(list);
            setError(null);
          }
        })
        .catch((e: unknown) => {
          if (!stopped) setError(e instanceof Error ? e.message : String(e));
        });
    };

    const connect = () => {
      socket = new WebSocket(WS_URL);
      socket.onopen = () => {
        setConnection("live");
        setConnectedAt(Date.now());
        loadDevices();
      };
      socket.onmessage = (event: MessageEvent<string>) => {
        const message = JSON.parse(event.data) as LiveMessage;
        if (message.type !== "reading") return;
        const reading = message.data;
        const key = keyOf(reading.source, reading.device_id);
        setDevices((current) => upsertDevice(current, reading));
        setReadingsByKey((current) => ({ ...current, [key]: merge(current[key] ?? [], [reading]) }));
      };
      socket.onclose = () => {
        if (stopped) return;
        setConnection("offline");
        retryTimer = setTimeout(connect, RECONNECT_MS);
      };
    };

    loadDevices();
    connect();
    return () => {
      stopped = true;
      clearTimeout(retryTimer);
      socket?.close();
    };
  }, []);

  // History of the shown device: when it changes, and after every reconnect (fills gaps)
  useEffect(() => {
    if (activeKey === null) return;
    const { source, deviceId } = parseKey(activeKey);
    let cancelled = false;
    api
      .history(MAX_READINGS, { source, deviceId })
      .then((history) => {
        if (!cancelled) {
          setReadingsByKey((current) => ({ ...current, [activeKey]: merge(current[activeKey] ?? [], history) }));
        }
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      });
    return () => {
      cancelled = true;
    };
  }, [activeKey, connectedAt]);

  const readings = useMemo(
    () => (activeKey === null ? [] : (readingsByKey[activeKey] ?? [])),
    [activeKey, readingsByKey],
  );
  const activeDevice = devices.find((d) => keyOf(d.source, d.device_id) === activeKey);

  return {
    devices,
    activeKey,
    readings,
    latest: readings.length > 0 ? readings[readings.length - 1] : null,
    totalStored: activeDevice?.readings ?? 0,
    thresholds,
    modelInfo,
    health,
    connection,
    error,
  };
}
