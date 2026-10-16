#include <Arduino.h>
#include <Wire.h>
#include "config.h"

static const uint8_t addresses[] = {0x18, 0x19, 0x1D, 0x1E, 0x68, 0x69};

static bool present(uint8_t address) {
  Wire.beginTransmission(address);
  return Wire.endTransmission() == 0;
}

static bool readRegister(uint8_t address, uint8_t reg, uint8_t &value) {
  Wire.beginTransmission(address);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0 || Wire.requestFrom(address, uint8_t(1)) != 1) return false;
  value = Wire.read();
  return true;
}

static bool readRegisters(uint8_t address, uint8_t reg, uint8_t *data, uint8_t length) {
  Wire.beginTransmission(address);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0 || Wire.requestFrom(address, length) != length) return false;
  for (uint8_t i = 0; i < length; ++i) data[i] = Wire.read();
  return true;
}

static bool writeRegister(uint8_t address, uint8_t reg, uint8_t value) {
  Wire.beginTransmission(address);
  Wire.write(reg);
  Wire.write(value);
  return Wire.endTransmission() == 0;
}

static void initializeSensors() {
  if (present(0x18) || present(0x19)) {
    uint8_t address = present(0x18) ? 0x18 : 0x19;
    writeRegister(address, 0x20, 0x27); // 10 Hz, all axes enabled
    writeRegister(address, 0x23, 0x08); // high-resolution, +/- 2 g
    Serial.printf("Accelerometer 0x%02X initialized\n", address);
  }
  if (present(0x1E)) {
    writeRegister(0x1E, 0x00, 0x70); // 8-sample average, 15 Hz
    writeRegister(0x1E, 0x01, 0x20); // gain
    writeRegister(0x1E, 0x02, 0x00); // continuous measurement
    Serial.println("Magnetometer 0x1E initialized");
  }
}

static void identify(uint8_t address) {
  uint8_t value = 0;
  if (readRegister(address, 0x0F, value)) {
    Serial.printf("  WHO_AM_I 0x%02X = 0x%02X", address, value);
    if (value == 0x33) Serial.print(" (LIS3DH/LSM303 accelerometer)");
    Serial.println();
  }
  if (address == 0x1E) {
    uint8_t id[3];
    if (readRegisters(address, 0x0A, id, sizeof(id))) {
      Serial.printf("  MAG ID: %c%c%c\n", id[0], id[1], id[2]);
    }
  }
}

static void readAccelerometer(uint8_t address) {
  uint8_t data[6];
  if (!readRegisters(address, 0x80 | 0x28, data, sizeof(data))) return;
  int16_t x = int16_t((uint16_t(data[1]) << 8) | data[0]);
  int16_t y = int16_t((uint16_t(data[3]) << 8) | data[2]);
  int16_t z = int16_t((uint16_t(data[5]) << 8) | data[4]);
  Serial.printf("  ACC 0x%02X: X=%d Y=%d Z=%d\n", address, x, y, z);
}

static void readMagnetometer() {
  uint8_t data[6];
  if (!readRegisters(0x1E, 0x03, data, sizeof(data))) return;
  int16_t x = int16_t((uint16_t(data[0]) << 8) | data[1]);
  int16_t z = int16_t((uint16_t(data[2]) << 8) | data[3]);
  int16_t y = int16_t((uint16_t(data[4]) << 8) | data[5]);
  Serial.printf("  MAG 0x1E: X=%d Y=%d Z=%d\n", x, y, z);
}

void setup() {
  Serial.begin(115200);
  Wire.begin(Pin::SDA, Pin::SCL, 100000);
  Wire.setTimeOut(20);
  delay(300);

  Serial.println();
  Serial.printf("GY-51 TEST: SDA=GPIO%d SCL=GPIO%d\n", Pin::SDA, Pin::SCL);
  Serial.println("Testing common accelerometer and magnetometer addresses...");
  initializeSensors();
}

void loop() {
  static uint32_t nextReport = 0;
  uint32_t now = millis();
  if (int32_t(now - nextReport) < 0) return;
  nextReport = now + 1000;

  bool found = false;
  for (uint8_t address : addresses) {
    if (!present(address)) continue;
    found = true;
    Serial.printf("I2C ACK 0x%02X\n", address);
    identify(address);
    if (address == 0x18 || address == 0x19) readAccelerometer(address);
  }
  if (present(0x1E)) readMagnetometer();
  if (!found) Serial.println("No GY-51 device found");
  Serial.println("---");
}