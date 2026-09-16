/*
===================================================================
Author/Maker : jihoonkimtech
Project      : Raw2Insight
File         : sketch.ino
Purpose      : Hardware interface for sensors and actuators
===================================================================
*/

#include "Arduino_RouterBridge.h"
#include <Wire.h>

/*
L Terminal blocks
- SCL    -> SCL
- SDA    -> SDA
- DIN01  -> D2
- DIN02  -> D4
- AIN01  -> A0
- AIN02  -> A1
- AIN03  -> A2
- AIN04  -> A3
- AIN05  -> A4
- AIN06  -> A5

R Terminal blocks
- POUT04 -> D6
- POUT03 -> D9
- POUT02 -> D10
- POUT01 -> D11
- VCC    -> +5V
- GND    -> GND
- DOUT04 -> D5
- DOUT03 -> D7
- DOUT02 -> D8
- DOUT01 -> D12

External power terminal
- VCC    -> +5V
- GND    -> GND
*/

bool valid_analog_pin(int pin_num) {
  return pin_num >= 0 && pin_num <= 5;
}

bool valid_digital_in_pin(int pin_num) {
  return pin_num == 2 || pin_num == 4;
}

bool valid_digital_out_pin(int pin_num) {
  return pin_num == 5 || pin_num == 7 || pin_num == 8 || pin_num == 12;
}

bool valid_pwm_pin(int pin_num) {
  return pin_num == 6 || pin_num == 9 || pin_num == 10 || pin_num == 11;
}

int read_analog(int pin_num) {
  if (pin_num < 0 || pin_num > 5) {
    Serial.print("[MCU] [ERROR] Invalid analog pin A");
    Serial.println(pin_num);
    return 0;
  }

  int actual_pin;
  switch (pin_num) {
    case 0: actual_pin = A0; break;
    case 1: actual_pin = A1; break;
    case 2: actual_pin = A2; break;
    case 3: actual_pin = A3; break;
    case 4: actual_pin = A4; break;
    case 5: actual_pin = A5; break;
    default: return 0;
  }

  int val = analogRead(actual_pin);
  return val;
}

int read_digital(int pin_num) {
  if (!valid_digital_in_pin(pin_num)) {
    Serial.print("[MCU] [ERROR] Invalid digital input pin D");
    Serial.println(pin_num);
    return 0;
  }

  pinMode(pin_num, INPUT);
  int val = digitalRead(pin_num);

  Serial.print("[MCU] [SENSOR READ] Digital Pin D");
  Serial.print(pin_num);
  Serial.print(" Read: ");
  Serial.println(val);

  return val;
}

// Collect up to read_bytes from the bus and pad missing bytes with zero
String collect_i2c_bytes(int addr, int read_bytes) {
  Wire.requestFrom(addr, read_bytes);

  String byteString = "";
  int count = 0;

  while (Wire.available() && count < read_bytes) {
    uint8_t b = Wire.read();
    byteString += String(b);
    count++;
    if (count < read_bytes) byteString += ",";
  }

  while (count < read_bytes) {
    if (count > 0) byteString += ",";
    byteString += "0";
    count++;
  }

  Serial.print("[MCU] Returning Bytes: ");
  Serial.println(byteString);

  return byteString;
}

String read_i2c_bytes(String addr_str, int read_bytes) {
  Serial.print("[MCU] [SENSOR READ] I2C Device (");
  Serial.print(addr_str);
  Serial.print(") Request Bytes: ");
  Serial.println(read_bytes);

  if (read_bytes <= 0) {
    return "";
  }

  int addr = (int) strtol(addr_str.c_str(), NULL, 0);
  return collect_i2c_bytes(addr, read_bytes);
}

// Set register pointer first, then read (for register-mapped sensors like MPU6050)
String read_i2c_reg(String addr_str, int reg, int read_bytes) {
  Serial.print("[MCU] [SENSOR READ] I2C Device (");
  Serial.print(addr_str);
  Serial.print(") Reg 0x");
  Serial.print(reg, HEX);
  Serial.print(" Request Bytes: ");
  Serial.println(read_bytes);

  if (read_bytes <= 0 || reg < 0 || reg > 0xFF) {
    return "";
  }

  int addr = (int) strtol(addr_str.c_str(), NULL, 0);

  Wire.beginTransmission(addr);
  Wire.write((uint8_t) reg);
  int result = Wire.endTransmission();
  if (result != 0) {
    // Return empty string so the Python side falls back to last good data
    Serial.print("[MCU] [ERROR] I2C register select failed: ");
    Serial.println(result);
    return "";
  }

  return collect_i2c_bytes(addr, read_bytes);
}

// Write comma-separated bytes in one transaction (e.g. "107,0" -> reg 0x6B = 0x00)
int write_i2c_bytes(String addr_str, String csv_bytes) {
  int addr = (int) strtol(addr_str.c_str(), NULL, 0);

  Wire.beginTransmission(addr);

  int start = 0;
  int written = 0;
  while (start < (int) csv_bytes.length()) {
    int comma = csv_bytes.indexOf(',', start);
    if (comma < 0) comma = csv_bytes.length();
    String token = csv_bytes.substring(start, comma);
    token.trim();
    if (token.length() > 0) {
      Wire.write((uint8_t) strtol(token.c_str(), NULL, 0));
      written++;
    }
    start = comma + 1;
  }

  int result = Wire.endTransmission();

  Serial.print("[MCU] [I2C WRITE] Device (");
  Serial.print(addr_str);
  Serial.print(") Bytes: ");
  Serial.print(written);
  Serial.print(" Result: ");
  Serial.println(result);

  // Return 1 on ACK, 0 on any bus error
  return (result == 0 && written > 0) ? 1 : 0;
}

// Iterations of a digitalRead loop per millisecond, measured once at boot
static uint32_t dht_loops_per_ms = 0;

static void dht_calibrate() {
  // Time a fixed number of the same loop body used by dht_capture (no timer call inside)
  const uint32_t probe_loops = 200000;
  pinMode(2, INPUT);
  unsigned long start = micros();
  uint32_t count = 0;
  while (count < probe_loops) {
    if (digitalRead(2) == 2) break;
    count++;
  }
  unsigned long elapsed_us = micros() - start;
  if (elapsed_us == 0) elapsed_us = 1;

  uint64_t per_ms = ((uint64_t) count * 1000ULL) / elapsed_us;
  dht_loops_per_ms = (per_ms < 1000) ? 1000 : (uint32_t) per_ms;

  Serial.print("[MCU] DHT loop calibration: ");
  Serial.print(dht_loops_per_ms);
  Serial.print(" loops/ms (");
  Serial.print(elapsed_us);
  Serial.println(" us)");
}

// Captured line segments: level and loop count for each run of equal level
#define DHT_MAX_SEGMENTS 100
static uint8_t dht_seg_level[DHT_MAX_SEGMENTS];
static uint32_t dht_seg_count[DHT_MAX_SEGMENTS];

// Record level runs until the line stays unchanged for timeout loops, returns segment count
static int dht_capture(int pin_num, uint32_t timeout) {
  int n = 0;
  int level = digitalRead(pin_num);
  uint32_t count = 0;
  while (n < DHT_MAX_SEGMENTS) {
    int now = digitalRead(pin_num);
    if (now == level) {
      if (++count >= timeout) {
        // Idle segment, mark with count 0 and stop
        dht_seg_level[n] = level;
        dht_seg_count[n] = 0;
        return n + 1;
      }
      continue;
    }
    dht_seg_level[n] = level;
    dht_seg_count[n] = count;
    n++;
    level = now;
    count = 1;
  }
  return n;
}

// Print the first segments for field debugging
static void dht_dump_segments(int n) {
  Serial.print("[MCU] DHT capture segments: ");
  Serial.print(n);
  Serial.print(" [");
  for (int i = 0; i < n && i < 8; ++i) {
    if (i > 0) Serial.print(" ");
    Serial.print(dht_seg_level[i] ? "H" : "L");
    Serial.print(dht_seg_count[i]);
  }
  Serial.println(n > 8 ? " ...]" : "]");
}

// Read 40 bits from a DHT sensor and return "b0,b1,b2,b3,b4" (empty string on failure)
String read_dht_bytes(int pin_num, int start_low_ms) {
  if (!valid_digital_in_pin(pin_num)) {
    Serial.print("[MCU] [ERROR] Invalid DHT pin D");
    Serial.println(pin_num);
    return "";
  }
  if (start_low_ms < 1 || start_low_ms > 30) start_low_ms = 20;

  // Idle line must be high (pull-up present)
  pinMode(pin_num, INPUT_PULLUP);
  delay(2);
  if (digitalRead(pin_num) == LOW) {
    Serial.println("[MCU] [ERROR] DHT line is LOW while idle (check VCC/GND/pull-up)");
    return "";
  }

  // Host start signal, also measure how long a pin reconfiguration takes
  unsigned long cfg_start = micros();
  pinMode(pin_num, OUTPUT);
  unsigned long cfg_us = micros() - cfg_start;
  digitalWrite(pin_num, LOW);
  delay(start_low_ms);
  if (digitalRead(pin_num) != LOW) {
    Serial.println("[MCU] [ERROR] DHT line stays HIGH while driven LOW (short to VCC?)");
    pinMode(pin_num, INPUT_PULLUP);
    return "";
  }

  // Lock first so no thread can delay listening after the release (~5ms total)
  uint32_t timeout = dht_loops_per_ms * 2;
  noInterrupts();
  pinMode(pin_num, INPUT_PULLUP);
  int n = dht_capture(pin_num, timeout);
  interrupts();

  // Align from the end: ... [L H]x40, L(end), H(idle)
  int end_low = -1;
  for (int i = n - 1; i >= 0; --i) {
    if (dht_seg_level[i] == LOW) { end_low = i; break; }
  }
  int first = end_low - 80;
  if (end_low < 0 || first < 0 || dht_seg_level[first] != LOW) {
    // 1 segment: sensor silent, 2..82 segments: listening started late or line noise
    Serial.print("[MCU] [ERROR] DHT incomplete frame, pinMode took ");
    Serial.print(cfg_us);
    Serial.println(" us");
    dht_dump_segments(n);
    return "";
  }

  uint8_t data[5] = {0, 0, 0, 0, 0};
  for (int i = 0; i < 40; ++i) {
    uint32_t low_cycles = dht_seg_count[first + 2 * i];
    uint32_t high_cycles = dht_seg_count[first + 2 * i + 1];
    data[i / 8] <<= 1;
    // High longer than the preceding low means bit 1
    if (high_cycles > low_cycles) data[i / 8] |= 1;
  }

  String byteString = "";
  for (int i = 0; i < 5; ++i) {
    if (i > 0) byteString += ",";
    byteString += String(data[i]);
  }

  Serial.print("[MCU] [SENSOR READ] DHT Pin D");
  Serial.print(pin_num);
  Serial.print(" Bytes: ");
  Serial.print(byteString);
  Serial.print(" (segments ");
  Serial.print(n);
  Serial.println(")");

  return byteString;
}

int read_i2c(String addr_str) {
  int addr = (int) strtol(addr_str.c_str(), NULL, 0);

  Wire.beginTransmission(addr);
  int result = Wire.endTransmission();

  Serial.print("[MCU] [SENSOR READ] I2C Device (");
  Serial.print(addr_str);
  Serial.print(") Probe Result: ");
  Serial.println(result == 0 ? 1 : 0);

  return (result == 0) ? 1 : 0;
}

// Current role of each output pin, avoids reconfiguring the pin on every write
enum OutMode { OUT_NONE = 0, OUT_GPIO = 1, OUT_PWM = 2 };
static uint8_t out_mode[22] = {0};

int write_digital(int pin_num, int val) {
  if (!valid_digital_out_pin(pin_num)) {
    Serial.print("[MCU] [ERROR] Invalid digital output pin D");
    Serial.println(pin_num);
    return 0;
  }

  PinStatus level = val > 0 ? HIGH : LOW;

  // Configure the pin once, reconfiguring on every call pulses it LOW on Zephyr
  if (out_mode[pin_num] != OUT_GPIO) {
    pinMode(pin_num, OUTPUT);
    out_mode[pin_num] = OUT_GPIO;
  }
  digitalWrite(pin_num, level);

  Serial.print("[MCU] [ACTUATOR CONTROL] Digital Pin D");
  Serial.print(pin_num);
  Serial.print(" Write: ");
  Serial.print(level == HIGH ? 1 : 0);
  Serial.print(" Readback: ");
  Serial.println(digitalRead(pin_num));

  return 1;
}

int write_pwm(int pin_num, int val) {
  if (!valid_pwm_pin(pin_num)) {
    Serial.print("[MCU] [ERROR] Invalid PWM pin D");
    Serial.println(pin_num);
    return 0;
  }

  int safe_val = constrain(val, 0, 255);

  // analogWrite applies the timer pinmux itself, calling pinMode(OUTPUT) here would detach it
  analogWrite(pin_num, safe_val);
  out_mode[pin_num] = OUT_PWM;

  Serial.print("[MCU] [ACTUATOR CONTROL] PWM Pin D");
  Serial.print(pin_num);
  Serial.print(" Write: ");
  Serial.println(safe_val);

  return 1;
}

void setup() {
  Serial.begin(9600);
  Bridge.begin();
  Wire.begin();
  dht_calibrate();

  pinMode(2, INPUT);
  pinMode(4, INPUT);

  // Safe default: all outputs off
  write_digital(5, 0);
  write_digital(7, 0);
  write_digital(8, 0);
  write_digital(12, 0);

  write_pwm(6, 0);
  write_pwm(9, 0);
  write_pwm(10, 0);
  write_pwm(11, 0);

  Bridge.provide("read_analog", read_analog);
  Bridge.provide("read_digital", read_digital);
  Bridge.provide("read_i2c_bytes", read_i2c_bytes);
  Bridge.provide("read_i2c_reg", read_i2c_reg);
  Bridge.provide("write_i2c_bytes", write_i2c_bytes);
  Bridge.provide("read_dht_bytes", read_dht_bytes);
  Bridge.provide("read_i2c", read_i2c);
  Bridge.provide("write_digital", write_digital);
  Bridge.provide("write_pwm", write_pwm);

  Serial.println("[MCU] Raw2Insight terminal-block router started.");
  Serial.println("[MCU] DIN : D2, D4");
  Serial.println("[MCU] AIN : A0~A5");
  Serial.println("[MCU] DOUT: D5, D7, D8, D12");
  Serial.println("[MCU] PWM : D6, D9, D10, D11");
  Serial.println("[MCU] I2C : SDA(D20), SCL(D21)");
  Serial.println("[MCU] DHT : D2, D4 (DIN terminals)");
}

void loop() {
}
