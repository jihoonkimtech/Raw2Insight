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
  if (!valid_analog_pin(pin_num)) {
    Serial.print("[MCU] [ERROR] Invalid analog pin A");
    Serial.println(pin_num);
    return 0;
  }

  int val = analogRead(pin_num);

  Serial.print("[MCU] [SENSOR READ] Analog Pin A");
  Serial.print(pin_num);
  Serial.print(" Read: ");
  Serial.println(val);

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

String read_i2c_bytes(String addr_str, int read_bytes) {
  Serial.print("[MCU] [SENSOR READ] I2C Device (");
  Serial.print(addr_str);
  Serial.print(") Request Bytes: ");
  Serial.println(read_bytes);

  if (read_bytes <= 0) {
    return "";
  }

  int addr = (int) strtol(addr_str.c_str(), NULL, 0);
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

int write_digital(int pin_num, int val) {
  if (!valid_digital_out_pin(pin_num)) {
    Serial.print("[MCU] [ERROR] Invalid digital output pin D");
    Serial.println(pin_num);
    return 0;
  }

  pinMode(pin_num, OUTPUT);
  digitalWrite(pin_num, val > 0 ? HIGH : LOW);

  Serial.print("[MCU] [ACTUATOR CONTROL] Digital Pin D");
  Serial.print(pin_num);
  Serial.print(" Write: ");
  Serial.println(val > 0 ? 1 : 0);

  return 1;
}

int write_pwm(int pin_num, int val) {
  if (!valid_pwm_pin(pin_num)) {
    Serial.print("[MCU] [ERROR] Invalid PWM pin D");
    Serial.println(pin_num);
    return 0;
  }

  int safe_val = constrain(val, 0, 255);

  pinMode(pin_num, OUTPUT);
  analogWrite(pin_num, safe_val);

  Serial.print("[MCU] [ACTUATOR CONTROL] PWM Pin D");
  Serial.print(pin_num);
  Serial.print(" Write: ");
  Serial.println(safe_val);

  return 1;
}

void setup() {
  Serial.begin(115200);
  Bridge.begin();
  Wire.begin();

  pinMode(2, INPUT);
  pinMode(4, INPUT);

  pinMode(5, OUTPUT);
  pinMode(7, OUTPUT);
  pinMode(8, OUTPUT);
  pinMode(12, OUTPUT);

  pinMode(6, OUTPUT);
  pinMode(9, OUTPUT);
  pinMode(10, OUTPUT);
  pinMode(11, OUTPUT);

  digitalWrite(5, LOW);
  digitalWrite(7, LOW);
  digitalWrite(8, LOW);
  digitalWrite(12, LOW);

  analogWrite(6, 0);
  analogWrite(9, 0);
  analogWrite(10, 0);
  analogWrite(11, 0);

  Bridge.provide("read_analog", read_analog);
  Bridge.provide("read_digital", read_digital);
  Bridge.provide("read_i2c_bytes", read_i2c_bytes);
  Bridge.provide("read_i2c", read_i2c);
  Bridge.provide("write_digital", write_digital);
  Bridge.provide("write_pwm", write_pwm);

  Serial.println("[MCU] Raw2Insight terminal-block router started.");
  Serial.println("[MCU] DIN : D2, D4");
  Serial.println("[MCU] AIN : A0~A5");
  Serial.println("[MCU] DOUT: D5, D7, D8, D12");
  Serial.println("[MCU] PWM : D6, D9, D10, D11");
  Serial.println("[MCU] I2C : SDA(D20), SCL(D21)");
}

void loop() {
}
