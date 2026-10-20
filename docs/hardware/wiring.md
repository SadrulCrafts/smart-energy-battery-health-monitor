# Hardware: wiring and safety

This is the Stage 4 test bench: one 18650 cell discharged through a 10 Ω resistor while an
Arduino Uno measures voltage, current and temperature once per second. The firmware is in
[`firmware/battery_monitor`](../../firmware/battery_monitor), the PC side in
[`backend/bridge.py`](../../backend/bridge.py).

> **Safety first.** A lithium-ion cell can deliver tens of amperes into a short circuit,
> enough to melt wires and start a fire. Follow the checklist below every time, never leave
> a discharge or a charge unattended, and keep the setup on a non-flammable surface.

## Parts

The parts actually used for this build (bought October 2026). Parts marked *optional* are
supported by the firmware but not needed to run the test.

| Part | Role | This build |
|---|---|---|
| Arduino Uno R3 compatible | Reads the sensors, switches the load, prints readings over USB | ATmega328P clone with CH340 USB chip, Type-C port |
| INA219 module | Measures cell voltage and current (I2C) | MCU-219, 0.1 Ω (R100) shunt, header pins already soldered |
| DS18B20 waterproof probe + adapter module | Measures cell surface temperature (1-Wire) | Adapter has the pull-up resistor and a screw terminal for the probe wires |
| 5 V single-channel relay module | Connects and disconnects the load | Optocoupler board, **low-level trigger** (`RELAY_ACTIVE_LOW = true`) |
| 10 Ω cement resistor | The load, about 0.4 A at 4.2 V (about 1.8 W) | 5 W rating (marked `5W10RJ`); runs hot, see below |
| Inline fuse holder with 1 A fuse | Protects against a short circuit | 5×20 mm glass fuse |
| 18650 cell + single holder | The cell under test | 2200 mAh rated (8140 mWh, seller's figure, not verified), button top; holder with 15 cm leads, no switch |
| Breadboard and jumper wires | Connections | 400 holes; 20 cm male-male and male-female |
| LED + 220 Ω resistor, active buzzer | Local warning | *optional*, not fitted in this build |
| Digital multimeter | Checking polarity and the sensor readings | *optional* but strongly recommended (borrow one if possible) |
| TP4056 module with protection | Charges the cell, outside the test rig | *not yet bought*: until then, no charging at all |

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
| DS18B20 probe red / black / yellow | Adapter screw terminal VCC / GND / DAT | Match the labels printed on the adapter |
| DS18B20 adapter VCC | Arduino 5V | |
| DS18B20 adapter GND | Arduino GND | |
| DS18B20 adapter DAT | Arduino D2 | The adapter has the 4.7 kΩ pull-up; a bare probe needs one from D2 to 5V |
| Relay VCC | Arduino 5V | |
| Relay GND | Arduino GND | |
| Relay IN | Arduino D7 | |
| LED anode (long leg) *(optional)* | Arduino D8 through 220 Ω | LED cathode to GND |
| Buzzer module I/O (or +) *(optional)* | Arduino D9 | Buzzer GND to GND |
| Cell − | Arduino GND | Common ground, see the power path |

Tape the DS18B20 probe to the **cell** with Kapton or electrical tape, away from the load
resistor.

**The load resistor gets hot.** At 0.4 A it turns about 1.8 W into heat, which a 5 W cement
resistor handles, but its surface can get too hot to touch. Keep it off the breadboard
plastic (lift it on its legs or rest it on a ceramic tile), do not touch it during a test,
and keep it away from the temperature probe so the probe measures the cell, not the resistor.

## Before the first power-up

1. **Relay type.** Many cheap relay modules switch on with a LOW input. Check the module's
   listing (高电平触发 = HIGH, 低电平触发 = LOW) and set `RELAY_ACTIVE_LOW` in the firmware.
2. **Cut-off voltage.** Check the cell's datasheet for its minimum discharge voltage and set
   `CUTOFF_V` (3.00 V by default, which is conservative for most cells).
3. **Polarity.** Check every connection to the cell holder before inserting the cell.
   Reversed polarity can destroy the INA219 and the Arduino.
4. **No short circuit.** With no cell inserted, measure the resistance between the holder's
   + and − terminals: it must not be close to 0 Ω.

### Without a multimeter

The checks above are easiest with a multimeter. Without one, do them by eye, slowly:

- The holder's red lead is + (the spring end is −). Mark the + lead with a piece of tape.
- Trace the + lead with a finger: holder + → fuse → INA219 VIN+. Nothing else may touch it.
- Trace the − lead: holder − → relay NO and Arduino GND.
- Make sure no bare wire end can touch another one.
- Insert the cell last, + end towards the + mark, with the USB cable already plugged in, and
  watch the first readings: `v` must be between about 3.3 and 4.2 V. If it is not, or if
  anything gets warm right away, pull the cell out.

The fuse protects against a short circuit, but it does not protect the INA219 from reversed
polarity, so this check matters. Without a multimeter the readings also cannot be
calibrated, so treat small differences (a few tens of millivolts) with care.

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
| Voltage at or below `CUTOFF_V` for 3 readings in a row | Load disconnected (3 beeps and LED on, if fitted) |
| Temperature at or above 45 °C for 3 readings in a row | Load disconnected |
| Temperature sensor lost during a discharge | Load disconnected |
| INA219 not found | Load stays off, `ERROR` line every second, LED blinks |
| Voltage below 3.20 V while discharging | LED blinks |

After a disconnect, the load stays off until the board is reset, so a person always decides
to start the next discharge.

## Charging

Charge the cell **outside the test rig**: take it out of the holder and charge it with the
TP4056 module (with protection), or with a proper Li-ion charger. This build has no charger
yet, so the first test uses the charge the cell arrived with; do not improvise charging
with a phone charger, a power bank or a bench supply. Never charge while the
discharge test is wired, never charge a damaged or hot cell, and never leave a charging
cell unattended.

## Limits of this setup

- The cell's rated capacity (2200 mAh) is the seller's figure. A discharge on this rig
  measures the capacity down to the 3.0 V cut-off only, which is less than the full rated
  capacity.
- The load draws about 0.4 A. The NASA cells the SoH model was trained on were discharged
  at 2 A, so the model is **not** validated for readings from this rig.
- The INA219 and DS18B20 are not calibrated instruments. Compare them with a multimeter and
  record the difference before trusting small changes.
