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
  Serial.print("[MCU] Analog Pin A"); Serial.print(pin_num);
  //Serial.print(" Read: "); Serial.println(val);
  Serial.print(" Read: "); Serial.println(dummyVal);
  //return val;
  return dummyVal;
}

int read_digital(int pin_num) {
  int dummyVal = random(0, 2);
  //pinMode(pin_num, INPUT);
  //int val = digitalRead(pin_num);
  Serial.print("[MCU] Digital Pin D"); Serial.print(pin_num);
  //Serial.print(" Read: "); Serial.println(val);
  Serial.print(" Read: "); Serial.println(dummyVal);
  //return val;
  return dummyVal;
}

int read_i2c(String addr_str) {
  int dummyVal = random(24, 48);
  Serial.print("[MCU] I2C Device ("); Serial.print(addr_str);
  Serial.print(") Read: "); Serial.println(dummyVal);
  return dummyVal;
}

void setup() {
  Bridge.begin();
  Serial.begin(115200);
  
  // register functions to bridge
  Bridge.provide("read_analog", read_analog);
  Bridge.provide("read_digital", read_digital);
  Bridge.provide("read_i2c", read_i2c);
}

void loop() {

}