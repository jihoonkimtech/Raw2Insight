/*
===================================================================
Author/Maker : jihoonkimtech
Project      : Raw2Insight
File         : sketch.ino
Purpose      : Hardware interface for sensors and actuators
===================================================================
*/
#include "Arduino_RouterBridge.h"

int read_analog(int pin_num) {
  int dummyVal = random(512, 1024);
  //int val = analogRead(pin_num);
  Serial.print("[MCU] [SENSOR READ] Analog Pin A"); Serial.print(pin_num);
  //Serial.print(" Read: "); Serial.println(val);
  Serial.print(" Read: "); Serial.println(dummyVal);
  //return val;
  return dummyVal;
}

int read_digital(int pin_num) {
  int dummyVal = random(0, 2);
  //pinMode(pin_num, INPUT);
  //int val = digitalRead(pin_num);
  Serial.print("[MCU] [SENSOR READ] Digital Pin D"); Serial.print(pin_num);
  //Serial.print(" Read: "); Serial.println(val);
  Serial.print(" Read: "); Serial.println(dummyVal);
  //return val;
  return dummyVal;
}

// AHT20 simulation
String read_i2c_bytes(String addr_str, int read_bytes) {
  Serial.print("[MCU] [SENSOR READ] I2C Device ("); 
  Serial.print(addr_str);
  Serial.print(") Request Bytes: "); 
  Serial.println(read_bytes);

  String byteString = "";

  // 0x38 is AHT20
  if (addr_str == "0x38" && read_bytes == 6) {
    float temp_c = random(200, 300) / 10.0;
    float hum_pct = random(400, 600) / 10.0;

    // make Raw
    uint32_t temp_raw = ((temp_c + 50.0) / 200.0) * 1048576.0;
    uint32_t hum_raw = (hum_pct / 100.0) * 1048576.0;

    // 6byte arr
    uint8_t data[6];
    data[0] = 0x18; // status bye
    data[1] = (hum_raw >> 12) & 0xFF;
    data[2] = (hum_raw >> 4) & 0xFF;
    data[3] = ((hum_raw & 0x0F) << 4) | ((temp_raw >> 16) & 0x0F);
    data[4] = (temp_raw >> 8) & 0xFF;
    data[5] = temp_raw & 0xFF;

    // assemble
    for (int i = 0; i < 6; i++) {
      byteString += String(data[i]);
      if (i < 5) byteString += ",";
    }
  } else {
    //if not AHT20? fill 0
    for (int i = 0; i < read_bytes; i++) {
      byteString += "0";
      if (i < read_bytes - 1) byteString += ",";
    }
  }

  Serial.print("[MCU] Returning Bytes: ");
  Serial.println(byteString);
  
  return byteString; 
}

int read_i2c(String addr_str) {
  int dummyVal = random(24, 48);
  Serial.print("[MCU] [SENSOR READ] I2C Device ("); Serial.print(addr_str);
  Serial.print(") Read: "); Serial.println(dummyVal);
  
  return dummyVal;

}

int write_digital(int pin_num, int val) {
  pinMode(pin_num, OUTPUT);
  Serial.print("[MCU] [ACTUATOR CONTROL] Digital Pin D"); Serial.print(pin_num);
  Serial.print(" Write: "); Serial.println(val);
  digitalWrite(pin_num, val > 0 ? HIGH : LOW);
  return 1;
}

int write_pwm(int pin_num, int val) {
  pinMode(pin_num, OUTPUT);
  Serial.print("[MCU] [ACTUATOR CONTROL] PWM Pin D"); Serial.print(pin_num);
  Serial.print(" Write: "); Serial.println(val);
  analogWrite(pin_num, val);
  return 1;
}

void setup() {
  Bridge.begin();
  Serial.begin(115200);
  
  // register functions to bridge
  Bridge.provide("read_analog", read_analog);
  Bridge.provide("read_digital", read_digital);
  Bridge.provide("read_i2c_bytes", read_i2c_bytes);
  Bridge.provide("read_i2c", read_i2c);
  Bridge.provide("write_digital", write_digital);
  Bridge.provide("write_pwm", write_pwm);

  Serial.println("[MCU] MCU is start running...");
}

void loop() {

}