# Firmware (Arduino Uno)

`battery_monitor/battery_monitor.ino` measures one 18650 cell once per second, protects it
with a relay cut-off, and prints readings over USB for [`backend/bridge.py`](../backend/bridge.py).
Wiring and safety: [docs/hardware/wiring.md](../docs/hardware/wiring.md).

## Upload

1. Install the **Arduino IDE** (version 2) from https://www.arduino.cc/en/software
2. Library Manager (left sidebar): install **Adafruit INA219** (accept its dependency
   Adafruit BusIO), **OneWire** and **DallasTemperature**.
3. Open `firmware/battery_monitor/battery_monitor.ino`.
4. Board: **Arduino Uno**. Port: the one that appears when the board is plugged in. Many
   compatible boards use a CH340 USB chip and show up as `USB-SERIAL CH340`; if no new port
   appears, install the CH340 driver.
5. Check the settings at the top of the file (`RELAY_ACTIVE_LOW`, `CUTOFF_V`).
6. Upload, then open the Serial Monitor at **115200 baud**.

Close the Serial Monitor before starting `bridge.py`: only one program can use the port.

## Output

One line per message:

```
INFO battery monitor firmware 1.0 starting
READING v=3.912 i=0.000 t=25.06 load=0
INFO load connected, discharge started
READING v=3.874 i=-0.384 t=25.19 load=1
INFO load disconnected: voltage at or below cut-off. Press reset to start again.
```

| Field | Meaning |
|---|---|
| `v` | Cell voltage in volts (INA219 bus voltage plus shunt voltage) |
| `i` | Current in amperes, negative while discharging |
| `t` | Cell temperature in °C, `nan` if the sensor is missing |
| `load` | `1` while the load relay is closed |

## Settings

| Setting | Default | Meaning |
|---|---|---|
| `CUTOFF_V` | 3.00 V | Disconnect the load at or below this voltage |
| `START_MIN_V` | 3.30 V | Only start a discharge above this voltage |
| `WARNING_V` | 3.20 V | LED blinks below this while discharging |
| `TEMP_CUTOFF_C` | 45 °C | Disconnect the load at or above this temperature |
| `CONFIRM_READINGS` | 3 | Readings in a row needed before a cut-off |
| `RELAY_ACTIVE_LOW` | `true` | Set to `false` if your relay switches on with HIGH |

## How it was checked before the hardware arrived

- Compiled for the Uno with all warnings enabled: about 14.8 KB of 32 KB flash and
  0.7 KB of 2 KB RAM.
- Its logic was run on a PC with simulated sensors: normal discharge to cut-off, a single
  glitchy reading (ignored), over-temperature, temperature sensor lost, a cell too low to
  start, and missing sensors. In every case the relay ended up in the safe state.
- Every line it prints was parsed by `bridge.py` without errors.

None of this replaces testing on the real board; follow the bring-up steps in the wiring guide.
