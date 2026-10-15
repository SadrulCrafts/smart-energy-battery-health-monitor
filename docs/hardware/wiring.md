# Hardware: wiring and safety

This is the Stage 4 test bench: one 18650 cell discharged through a 10 Ω resistor while an
Arduino Uno measures voltage, current and temperature once per second. The firmware is in
[`firmware/battery_monitor`](../../firmware/battery_monitor), the PC side in
[`backend/bridge.py`](../../backend/bridge.py).

> **Safety first.** A lithium-ion cell can deliver tens of amperes into a short circuit,
> enough to melt wires and start a fire. Follow the checklist below every time, never leave
> a discharge or a charge unattended, and keep the setup on a non-flammable surface.

## Parts

| Part | Role |
|---|---|
| Arduino Uno R3 (or compatible) | Reads the sensors, switches the load, prints readings over USB |
| INA219 module | Measures cell voltage and current (I2C) |
| DS18B20 waterproof probe | Measures cell surface temperature (1-Wire) |
| 4.7 kΩ resistor | Pull-up for the DS18B20 data line (often already on the probe's module) |
| 5 V single-channel relay module | Connects and disconnects the load |
| 10 Ω, 10 W aluminium-housed resistor | The load, about 0.4 A at 4.2 V (about 1.8 W) |
| Inline fuse holder with 1 A fuse | Protects against a short circuit |
| 18650 cell (genuine brand) + single holder | The cell under test |
| TP4056 module with protection | Charges the cell, separately from the test (see Charging) |
| LED + 220 Ω resistor, active buzzer module | Local warning |
| Digital multimeter | Checking voltages and the sensor readings |

## Power path (the part that carries current)

```
 Cell +  ──[ 1 A fuse ]──►  INA219 VIN+
                            INA219 VIN-  ──►  10 Ω 10 W resistor  ──►  Relay COM
                                                                       Relay NO  ──►  Cell −

 Cell −  ──►  Arduino GND   (common ground: the INA219 measures voltage against GND)
```

- The fuse is the **first** thing after the cell's positive terminal.
- Use the relay's **NO** (normally open) contact, so the load is disconnected whenever the
  relay is not powered.
- Current flows into VIN+ and out of VIN−. The firmware reports it as negative (discharging).
- With the relay open, VIN− still sits at the cell voltage through the shunt, so the resting
  (open-circuit) voltage is still measured.

## Signal wiring

| From | To | Note |
|---|---|---|
| INA219 VCC | Arduino 5V | |
| INA219 GND | Arduino GND | |
| INA219 SDA | Arduino A4 | |
| INA219 SCL | Arduino A5 | |
| DS18B20 red (VCC) | Arduino 5V | |
| DS18B20 black (GND) | Arduino GND | |
| DS18B20 yellow (data) | Arduino D2 | 4.7 kΩ from D2 to 5V if the probe has no module |
| Relay VCC | Arduino 5V | |
| Relay GND | Arduino GND | |
| Relay IN | Arduino D7 | |
| LED anode (long leg) | Arduino D8 through 220 Ω | LED cathode to GND |
| Buzzer module I/O (or +) | Arduino D9 | Buzzer GND to GND |
| Cell − | Arduino GND | Common ground, see the power path |

Tape the DS18B20 probe to the **cell** with Kapton tape, away from the load resistor,
which gets warm.

## Before the first power-up

1. **Relay type.** Many cheap relay modules switch on with a LOW input. Check the module's
   listing (高电平触发 = HIGH, 低电平触发 = LOW) and set `RELAY_ACTIVE_LOW` in the firmware.
2. **Cut-off voltage.** Check the cell's datasheet for its minimum discharge voltage and set
   `CUTOFF_V` (3.00 V by default, which is conservative for most cells).
3. **Polarity.** Check every connection to the cell holder with the multimeter before
   inserting the cell. Reversed polarity can destroy the INA219 and the Arduino.
4. **No short circuit.** With no cell inserted, measure the resistance between the holder's
   + and − terminals: it must not be close to 0 Ω.

## Bring-up, one step at a time

1. **Arduino and INA219 only** (no cell, no relay). Upload the firmware and open the Serial
   Monitor at 115200 baud. Expect `INFO battery monitor firmware 1.0 starting` and no
   `ERROR INA219 not found`. `ERROR DS18B20 not found` is expected at this step.
2. **Add the DS18B20.** Reset. The readings should show a room temperature for `t`.
3. **Add the relay** without the load wired to it. After reset you hear it stay silent
   (cell missing, so the firmware refuses to start the discharge).
4. **Insert the cell, load still disconnected.** Compare `v` with the multimeter across the
   cell. They should agree within a few tens of millivolts.
5. **Connect the load.** Reset. After 3 seconds you should hear the relay click and see
   `INFO load connected, discharge started` and `i` around −0.38 A. Check the current with
   the multimeter in series if possible.
6. **Close the Serial Monitor**, then start the bridge:
   `python backend/bridge.py --port COM5` (use the port from `--list-ports`).

## What the firmware does on its own

| Situation | Action |
|---|---|
| Power-up | Relay off; measures the resting cell for 3 s |
| Cell below 3.30 V, too warm, or no temperature reading at start | Discharge not started |
| Voltage at or below `CUTOFF_V` for 3 readings in a row | Load disconnected, 3 beeps, LED on |
| Temperature at or above 45 °C for 3 readings in a row | Load disconnected |
| Temperature sensor lost during a discharge | Load disconnected |
| INA219 not found | Load stays off, `ERROR` line every second, LED blinks |
| Voltage below 3.20 V while discharging | LED blinks |

After a disconnect, the load stays off until the board is reset, so a person always decides
to start the next discharge.

## Charging

Charge the cell **outside the test rig**: take it out of the holder and charge it with the
TP4056 module (with protection), or with a proper Li-ion charger. Never charge while the
discharge test is wired, never charge a damaged or hot cell, and never leave a charging
cell unattended.

## Limits of this setup

- The load draws about 0.4 A. The NASA cells the SoH model was trained on were discharged
  at 2 A, so the model is **not** validated for readings from this rig.
- The INA219 and DS18B20 are not calibrated instruments. Compare them with a multimeter and
  record the difference before trusting small changes.
