/*
===================================================================
Author/Maker : jihoonkimtech
Project      : Raw2Insight
File         : sketch.ino
Purpose      : Hardware interface for sensors and actuators
===================================================================
*/
#include "Arduino_RouterBridge.h"

int dummySensorValue = 0;

int get_sensor_data() {
  dummySensorValue = random(1,1024);
  Serial.print("get_sensor_data() procedure called! return value is ");
  Serial.println(dummySensorValue);
  return dummySensorValue;
}

void setup() {
  Bridge.begin();
  Serial.begin(115200);
  
  Bridge.provide("get_sensor_data", get_sensor_data);
}

void loop() {

}