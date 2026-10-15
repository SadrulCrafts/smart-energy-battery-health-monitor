"""
bridge.py
---------
Stage 4: read measurements from the Arduino over USB (serial) and send each one
to the backend (POST /readings).

Line format sent by the Arduino (one line per message, 115200 baud):

    READING v=3.842 i=-0.381 t=26.40 load=1
        v     cell voltage in volts
        i     current in amperes, NEGATIVE while discharging
        t     cell temperature in degrees C, or "nan" if the sensor is missing
        load  1 = load relay closed (discharging), 0 = open (optional)
    INFO <text>     status messages (printed, not stored)
    ERROR <text>    problems reported by the Arduino (printed, not stored)

Data sources stay honest:
    --port COM3   real Arduino   -> stored as source = "sensor"
    --fake        fake Arduino   -> stored as source = "simulated"

Run from the project root, with the backend already running:
    python backend/bridge.py --list-ports            # which COM port is the Arduino?
    python backend/bridge.py --port COM3             # real hardware
    python backend/bridge.py --fake                  # test everything without hardware
    python backend/bridge.py --port COM3 --dry-run   # print only, send nothing
Stop with Ctrl+C.
"""

import argparse
import math
import sys
import threading
import time

from simulator import SimulatedCell, send_reading

BAUD_RATE = 115200
DS18B20_DISCONNECTED_C = -127.0   # value the DallasTemperature library returns for a missing sensor


def format_reading_line(voltage_v, current_a, temperature_c, load_on):
    """One READING line, exactly as the firmware prints it."""
    t = "nan" if temperature_c is None else f"{temperature_c:.2f}"
    return f"READING v={voltage_v:.3f} i={current_a:.3f} t={t} load={1 if load_on else 0}\n"


def parse_line(line):
    """
    Turn one line from the Arduino into (kind, data):
        ("reading", {"voltage_v", "current_a", "temperature_c", "load_on"})
        ("info", text) / ("error", text)
        ("invalid", reason)   -> ignored (for example half a line right after connecting)
    """
    line = line.strip()
    if not line:
        return "invalid", "empty line"
    kind, _, rest = line.partition(" ")
    if kind == "INFO":
        return "info", rest
    if kind == "ERROR":
        return "error", rest
    if kind != "READING":
        return "invalid", f"unknown line: {line[:60]!r}"

    fields = {}
    for part in rest.split():
        key, sep, value = part.partition("=")
        if not sep:
            return "invalid", f"bad field {part!r}"
        fields[key] = value

    try:
        voltage = float(fields["v"])
        current = float(fields["i"])
        temperature = float(fields.get("t", "nan"))
    except (KeyError, ValueError):
        return "invalid", f"missing or unreadable v / i / t in {line[:60]!r}"
    if not (math.isfinite(voltage) and math.isfinite(current)):
        return "invalid", "voltage or current is not a number"

    if not math.isfinite(temperature) or temperature <= DS18B20_DISCONNECTED_C + 0.5:
        temperature = None                       # sensor missing: store "no temperature"

    load = fields.get("load")
    return "reading", {
        "voltage_v": voltage,
        "current_a": current,
        "temperature_c": temperature,
        "load_on": None if load is None else load == "1",
    }


def build_payload(reading, source, device_id):
    """The JSON body for POST /readings (the load state is printed, not stored)."""
    return {
        "source": source,
        "device_id": device_id,
        "voltage_v": round(reading["voltage_v"], 4),
        "current_a": round(reading["current_a"], 4),
        "temperature_c": None if reading["temperature_c"] is None else round(reading["temperature_c"], 2),
    }


class FakeArduino:
    """
    Writes lines in the firmware's format into a serial port, using the simulator's
    made-up cell model. Lets the whole serial path be tested without hardware.
    """

    def __init__(self, port, interval_s=1.0, speed=60.0):
        self.port = port
        self.interval_s = interval_s
        self.speed = speed
        self.cell = SimulatedCell()
        self.stop = threading.Event()

    def lines(self, count):
        """The next `count` lines (also used by the tests)."""
        out = []
        for n in range(count):
            voltage, current, temperature = self.cell.step(self.interval_s * self.speed)
            out.append(format_reading_line(voltage, current, temperature, self.cell.phase == "discharge"))
            if n % 30 == 29:
                out.append("INFO fake Arduino heartbeat\n")
        return out

    def run(self):
        self.port.write(b"\x00\x13garbage from a reset\n")   # real boards send noise when the port opens
        self.port.write(b"INFO fake Arduino started\n")
        while not self.stop.is_set():
            for line in self.lines(1):
                self.port.write(line.encode("ascii"))
            self.stop.wait(self.interval_s)


def open_port(args):
    try:
        import serial
    except ImportError:
        sys.exit("pyserial is not installed. Run:  pip install -r backend/requirements.txt")
    if args.fake:
        # "loop://" is a serial port in memory: what is written comes back out
        return serial.serial_for_url("loop://", timeout=1)
    try:
        return serial.Serial(args.port, BAUD_RATE, timeout=1)
    except serial.SerialException as exc:
        sys.exit(f"Could not open {args.port}: {exc}\n"
                 "Check the port with --list-ports and close the Arduino IDE Serial Monitor.")


def list_ports():
    try:
        from serial.tools import list_ports as lp
    except ImportError:
        sys.exit("pyserial is not installed. Run:  pip install -r backend/requirements.txt")
    ports = list(lp.comports())
    if not ports:
        print("No serial ports found. Is the Arduino plugged in?")
    for port in ports:
        print(f"{port.device:<10} {port.description}")


def main():
    parser = argparse.ArgumentParser(description="Forward Arduino readings to the backend.")
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--port", help="serial port of the Arduino, for example COM3")
    target.add_argument("--fake", action="store_true", help="use a fake Arduino (data labeled simulated)")
    target.add_argument("--list-ports", action="store_true", help="show available serial ports")
    parser.add_argument("--url", default="http://127.0.0.1:8000/readings")
    parser.add_argument("--device-id", default=None, help="default: arduino-uno-1 (or fake-arduino)")
    parser.add_argument("--dry-run", action="store_true", help="print readings, send nothing")
    parser.add_argument("--speed", type=float, default=60.0, help="--fake only: simulated seconds per second")
    args = parser.parse_args()

    if args.list_ports:
        list_ports()
        return

    source = "simulated" if args.fake else "sensor"
    device_id = args.device_id or ("fake-arduino" if args.fake else "arduino-uno-1")
    port = open_port(args)

    fake = None
    if args.fake:
        fake = FakeArduino(port, interval_s=1.0, speed=args.speed)
        threading.Thread(target=fake.run, daemon=True).start()

    print(f"Reading {'FAKE Arduino' if args.fake else args.port} -> "
          f"{'(dry run)' if args.dry_run else args.url}  as source={source}, device={device_id}")
    print("Press Ctrl+C to stop.")

    sent = failed = ignored = 0
    try:
        while True:
            raw = port.readline()                        # waits at most 1 s
            if not raw:
                continue
            kind, data = parse_line(raw.decode("ascii", errors="replace"))
            if kind == "info":
                print(f"[arduino] {data}")
            elif kind == "error":
                print(f"[arduino ERROR] {data}")
            elif kind == "invalid":
                ignored += 1
                print(f"[ignored] {data}")
            else:
                payload = build_payload(data, source, device_id)
                load = {True: "load on", False: "load off", None: ""}[data["load_on"]]
                temp = "n/a" if payload["temperature_c"] is None else f"{payload['temperature_c']:.2f} C"
                summary = (f"V={payload['voltage_v']:.3f}  I={payload['current_a']:+.3f}  "
                           f"T={temp}  {load}")
                if args.dry_run:
                    print(f"[dry run] {summary}")
                    continue
                ok, message = send_reading(args.url, payload)
                sent, failed = (sent + 1, failed) if ok else (sent, failed + 1)
                print(f"[{'sent' if ok else 'FAILED'}] {summary}  -> {message}")
    except KeyboardInterrupt:
        print(f"\nStopped. sent={sent} failed={failed} ignored={ignored}")
    finally:
        if fake:
            fake.stop.set()
            time.sleep(0.1)
        port.close()


if __name__ == "__main__":
    main()
