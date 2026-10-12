"""
simulator.py
------------
Stage 3, Step 4: send SIMULATED battery readings to the backend.

This script pretends to be a measurement device. It sends readings to
POST /readings exactly the way the Arduino bridge will later, but every
reading is labeled  source = "simulated"  so it can never be mistaken for a
real measurement.

The numbers come from a simple made-up model of one 18650 cell connected to a
10-ohm load. They are NOT measurements and NOT NASA data.

Cycle:  discharge (until 3.0 V)  ->  rest  ->  charge (until 4.2 V)  ->  rest  -> ...

Run from the project root (with the backend already running in another terminal):
    python backend/simulator.py
Options:
    python backend/simulator.py --interval 1 --speed 120
    python backend/simulator.py --steps 20        (send 20 readings, then stop)
Stop with Ctrl+C.
"""

import argparse
import json
import random
import time
import urllib.error
import urllib.request

# --- Simple, made-up cell model (for demonstration only) -------------------
CAPACITY_AH = 1.8          # pretend the cell has 90% of a 2.0 Ah rating
LOAD_OHM = 10.0            # matches the planned 10-ohm load resistor
INTERNAL_OHM = 0.08        # pretend internal resistance
CHARGE_CURRENT_A = 0.5
DISCHARGE_CUTOFF_V = 3.0
CHARGE_END_V = 4.2
REST_STEPS = 5
AMBIENT_C = 25.0
HEATING_C_PER_A2 = 0.75    # made-up: gives a rise of only a few degrees at these currents
COOLING_RATE = 0.05

# Open-circuit voltage vs state of charge (rough Li-ion shape)
OCV_TABLE = [(0.00, 3.00), (0.05, 3.30), (0.10, 3.45), (0.20, 3.55), (0.40, 3.65),
             (0.60, 3.78), (0.80, 3.95), (0.90, 4.05), (1.00, 4.20)]


def open_circuit_voltage(soc):
    soc = min(max(soc, 0.0), 1.0)
    for (s0, v0), (s1, v1) in zip(OCV_TABLE, OCV_TABLE[1:]):
        if soc <= s1:
            return v0 + (v1 - v0) * (soc - s0) / (s1 - s0)
    return OCV_TABLE[-1][1]


class SimulatedCell:
    def __init__(self):
        self.soc = 1.0
        self.phase = "discharge"
        self.rest_left = 0
        self.next_phase = "charge"
        self.temperature_c = AMBIENT_C

    def step(self, dt_s):
        """Advance the model by dt_s simulated seconds and return (V, I, T)."""
        ocv = open_circuit_voltage(self.soc)

        if self.phase == "discharge":
            current = -ocv / (LOAD_OHM + INTERNAL_OHM)          # negative = discharge
            voltage = ocv + current * INTERNAL_OHM
            self.soc += current * dt_s / 3600 / CAPACITY_AH
            if voltage <= DISCHARGE_CUTOFF_V:
                self.phase, self.rest_left, self.next_phase = "rest", REST_STEPS, "charge"
        elif self.phase == "charge":
            current = CHARGE_CURRENT_A
            voltage = min(ocv + current * INTERNAL_OHM, CHARGE_END_V)
            self.soc += current * dt_s / 3600 / CAPACITY_AH
            if voltage >= CHARGE_END_V or self.soc >= 1.0:
                self.soc = min(self.soc, 1.0)
                self.phase, self.rest_left, self.next_phase = "rest", REST_STEPS, "discharge"
        else:  # rest
            current = 0.0
            voltage = ocv
            self.rest_left -= 1
            if self.rest_left <= 0:
                self.phase = self.next_phase

        # Temperature: warms with current (I^2 R heating), cools toward ambient
        heating = (current ** 2) * HEATING_C_PER_A2
        cooling = (self.temperature_c - AMBIENT_C) * COOLING_RATE
        self.temperature_c += (heating - cooling) * min(dt_s / 60, 1)

        noise = random.gauss
        return (round(voltage + noise(0, 0.003), 3),
                round(current + noise(0, 0.002), 3),
                round(self.temperature_c + noise(0, 0.05), 2))


def send_reading(url, payload, timeout=5):
    """POST one reading. Returns (ok, message)."""
    request = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
            return True, f"stored id={body.get('id')}"
    except urllib.error.HTTPError as exc:
        return False, f"HTTP {exc.code}: {exc.read().decode('utf-8', errors='replace')[:200]}"
    except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
        return False, f"backend not reachable ({exc}). Is uvicorn running?"


def main():
    parser = argparse.ArgumentParser(description="Send SIMULATED battery readings to the API.")
    parser.add_argument("--url", default="http://127.0.0.1:8000/readings")
    parser.add_argument("--interval", type=float, default=2.0, help="real seconds between readings")
    parser.add_argument("--speed", type=float, default=60.0,
                        help="simulated seconds per real second (60 = one minute per second)")
    parser.add_argument("--steps", type=int, default=0, help="stop after N readings (0 = run forever)")
    parser.add_argument("--device-id", default="simulator-1")
    args = parser.parse_args()

    cell = SimulatedCell()
    print(f"Sending SIMULATED readings to {args.url} every {args.interval} s "
          f"(x{args.speed:g} time). Press Ctrl+C to stop.")
    sent = 0
    try:
        while args.steps == 0 or sent < args.steps:
            voltage, current, temperature = cell.step(args.interval * args.speed)
            payload = {
                "source": "simulated",
                "device_id": args.device_id,
                "voltage_v": voltage,
                "current_a": current,
                "temperature_c": temperature,
            }
            ok, message = send_reading(args.url, payload)
            sent += 1
            print(f"[{sent:4d}] {cell.phase:<9} V={voltage:5.3f}  I={current:+6.3f}  "
                  f"T={temperature:5.2f}  -> {'OK ' if ok else 'ERR'} {message}")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nStopped by user.")


if __name__ == "__main__":
    main()