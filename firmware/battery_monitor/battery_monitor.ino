/*
  battery_monitor.ino
  -------------------
  Stage 4 firmware for the Battery Health Monitor (Arduino Uno R3).

  Measures one 18650 cell once per second and prints one line over USB:
      READING v=3.842 i=-0.381 t=26.40 load=1
  backend/bridge.py reads these lines and sends them to the backend.

  Safety runs HERE, on the Arduino, so it also works when the PC is off:
    - the load relay is OFF at power-up and whenever something is wrong
    - the load is disconnected at the cut-off voltage (3 readings in a row),
      on over-temperature, or when the temperature sensor is lost
    - after a cut-off the load stays off until the board is reset
      (press the reset button or re-plug USB): a human decides to restart

  Wiring (details: docs/hardware/wiring.md)
    INA219   VCC 5V, GND GND, SDA A4, SCL A5, VIN+ from fuse, VIN- to load resistor
    DS18B20  data D2 (4.7 kOhm pull-up to 5V), VCC 5V, GND GND
    Relay    IN D7, VCC 5V, GND GND; contacts in series with the load (COM / NO)
    LED      D8 through 220 Ohm to GND
    Buzzer   D9 (active buzzer module)
    Battery negative must be connected to Arduino GND (common ground).

  Libraries (Arduino IDE > Library Manager):
    Adafruit INA219, OneWire, DallasTemperature
*/

#include <Wire.h>
#include <Adafruit_INA219.h>
#include <OneWire.h>
#include <DallasTemperature.h>

// ---------------------------------------------------------------------------
// Settings: CHECK THESE AGAINST YOUR OWN PARTS BEFORE THE FIRST RUN
// ---------------------------------------------------------------------------
const float CUTOFF_V = 3.00;          // disconnect the load at or below this (check the cell datasheet)
const float START_MIN_V = 3.30;       // only start a discharge above this voltage
const float WARNING_V = 3.20;         // LED blinks below this
const float TEMP_CUTOFF_C = 45.0;     // disconnect the load at or above this temperature
const uint8_t CONFIRM_READINGS = 3;   // readings in a row before a cut-off (ignores one-off glitches)
const bool RELAY_ACTIVE_LOW = true;   // most cheap relay modules switch ON with LOW. Check yours!
const unsigned long PERIOD_MS = 1000; // one reading per second
const unsigned long START_DELAY_MS = 3000;  // measure the resting cell before connecting the load

// Pins
const uint8_t PIN_TEMP = 2;
const uint8_t PIN_RELAY = 7;
const uint8_t PIN_LED = 8;
const uint8_t PIN_BUZZER = 9;

// ---------------------------------------------------------------------------
Adafruit_INA219 ina219;
OneWire oneWire(PIN_TEMP);
DallasTemperature tempSensors(&oneWire);

enum State { STARTING, RUNNING, STOPPED, FAULT };
State state = STARTING;
bool tempSensorFound = false;
uint8_t lowCount = 0;
uint8_t hotCount = 0;
unsigned long lastReadingMs = 0;

// Forward declarations
void setRelay(bool on);
void stopLoad(const char *reason);
void beep(uint8_t times);
void updateLed(float voltage);
float readTemperature();
void printReading(float voltage, float current, float temperature);

void setup() {
  // Relay OFF before the pin becomes an output, so the load never clicks on at power-up
  digitalWrite(PIN_RELAY, RELAY_ACTIVE_LOW ? HIGH : LOW);
  pinMode(PIN_RELAY, OUTPUT);
  pinMode(PIN_LED, OUTPUT);
  pinMode(PIN_BUZZER, OUTPUT);

  Serial.begin(115200);
  Serial.println(F("INFO battery monitor firmware 1.0 starting"));

  if (!ina219.begin()) {
    state = FAULT;
    Serial.println(F("ERROR INA219 not found: check SDA A4, SCL A5, VCC and GND. Load stays off."));
    return;
  }
  ina219.setCalibration_32V_1A();     // up to about 1.3 A, finer resolution than the 2 A setting

  tempSensors.begin();
  tempSensors.setResolution(12);
  tempSensors.setWaitForConversion(false);   // do not block the loop for 750 ms
  tempSensorFound = tempSensors.getDeviceCount() > 0;
  if (tempSensorFound) {
    tempSensors.requestTemperatures();
  } else {
    Serial.println(F("ERROR DS18B20 not found: check D2, the 4.7 kOhm pull-up, VCC and GND. Load stays off."));
  }
}

void loop() {
  unsigned long now = millis();
  if (now - lastReadingMs < PERIOD_MS) {
    return;
  }
  lastReadingMs = now;

  if (state == FAULT) {
    setRelay(false);
    digitalWrite(PIN_LED, !digitalRead(PIN_LED));   // fast blink: wiring problem
    Serial.println(F("ERROR INA219 not found. Fix the wiring and press reset."));
    return;
  }

  // Cell voltage = bus voltage (VIN- to GND) + drop across the shunt
  float voltage = ina219.getBusVoltage_V() + ina219.getShuntVoltage_mV() / 1000.0;
  // INA219 counts current flowing VIN+ -> VIN- (discharge) as positive; the project uses negative
  float current = -ina219.getCurrent_mA() / 1000.0;
  if (fabs(current) < 0.0005) {
    current = 0.0;                       // print 0.000 instead of -0.000
  }
  float temperature = readTemperature();   // NAN if the sensor is missing
  bool tempOk = !isnan(temperature);

  if (state == STARTING && now >= START_DELAY_MS) {
    if (!tempOk) {
      stopLoad("no temperature reading, load not started");
    } else if (voltage <= START_MIN_V) {
      stopLoad("cell voltage too low to start a discharge");
    } else if (temperature >= TEMP_CUTOFF_C) {
      stopLoad("cell too warm to start a discharge");
    } else {
      state = RUNNING;
      setRelay(true);
      Serial.println(F("INFO load connected, discharge started"));
    }
  } else if (state == RUNNING) {
    lowCount = (voltage <= CUTOFF_V) ? lowCount + 1 : 0;
    hotCount = (tempOk && temperature >= TEMP_CUTOFF_C) ? hotCount + 1 : 0;
    if (!tempOk) {
      stopLoad("temperature sensor lost");
    } else if (lowCount >= CONFIRM_READINGS) {
      stopLoad("voltage at or below cut-off");
    } else if (hotCount >= CONFIRM_READINGS) {
      stopLoad("temperature at or above limit");
    }
  }

  updateLed(voltage);
  printReading(voltage, current, temperature);
}

void setRelay(bool on) {
  bool level = RELAY_ACTIVE_LOW ? !on : on;
  digitalWrite(PIN_RELAY, level ? HIGH : LOW);
}

void stopLoad(const char *reason) {
  setRelay(false);
  if (state != STOPPED) {
    state = STOPPED;
    Serial.print(F("INFO load disconnected: "));
    Serial.print(reason);
    Serial.println(F(". Press reset to start again."));
    beep(3);
  }
}

void beep(uint8_t times) {
  for (uint8_t n = 0; n < times; n++) {
    digitalWrite(PIN_BUZZER, HIGH);
    delay(120);
    digitalWrite(PIN_BUZZER, LOW);
    delay(120);
  }
}

void updateLed(float voltage) {
  if (state == STOPPED) {
    digitalWrite(PIN_LED, HIGH);                     // solid: load is off after a cut-off
  } else if (state == RUNNING && voltage <= WARNING_V) {
    digitalWrite(PIN_LED, !digitalRead(PIN_LED));    // blinking: close to cut-off
  } else {
    digitalWrite(PIN_LED, LOW);
  }
}

float readTemperature() {
  if (!tempSensorFound) {
    return NAN;
  }
  float t = tempSensors.getTempCByIndex(0);   // result of the conversion started one second ago
  tempSensors.requestTemperatures();           // start the next one
  if (t == DEVICE_DISCONNECTED_C || t == 85.0) {
    return NAN;                                // -127 = no sensor, 85 = power-on value (not a measurement)
  }
  return t;
}

void printReading(float voltage, float current, float temperature) {
  Serial.print(F("READING v="));
  Serial.print(voltage, 3);
  Serial.print(F(" i="));
  Serial.print(current, 3);
  Serial.print(F(" t="));
  if (isnan(temperature)) {
    Serial.print(F("nan"));
  } else {
    Serial.print(temperature, 2);
  }
  Serial.print(F(" load="));
  Serial.println(state == RUNNING ? 1 : 0);
}
