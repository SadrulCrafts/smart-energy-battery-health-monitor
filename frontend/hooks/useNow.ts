"use client";

/**
 * useNow.ts
 * ---------
 * The current time in whole seconds, updated every second.
 * Used for text like "updated 3 s ago". Returns 0 during server rendering.
 */

import { useSyncExternalStore } from "react";

function subscribe(onChange: () => void) {
  const timer = setInterval(onChange, 1000);
  return () => clearInterval(timer);
}

export function useNow(): number {
  return useSyncExternalStore(
    subscribe,
    () => Math.floor(Date.now() / 1000),
    () => 0,
  );
}
