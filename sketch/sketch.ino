#include "Arduino_RouterBridge.h"

int dummySensorValue = 0;

int get_sensor_data() {
  dummySensorValue = (dummySensorValue + 1) % 100;
  return dummySensorValue;
}

void setup() {
  Bridge.begin();
  
  Bridge.provide("get_sensor_data", get_sensor_data);
}

void loop() {

}