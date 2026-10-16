#pragma once
#include <stdint.h>

namespace Pin {
// Confirmed by the user on 2026-09-10: DC is wired to 7, CS to 6.
constexpr int SCK = 10, MOSI = 11, CS = 6, DC = 7, RST = 5;
constexpr int SDA = 8, SCL = 9;
// UART1: cross GPS TX -> GPS_RX, GPS RX -> GPS_TX.
constexpr int GPS_RX = 12, GPS_TX = 13;
constexpr int BUTTON = 4, SOUND = 2;
constexpr uint8_t PAGE_COUNT = 11;
}

constexpr uint32_t GPS_BAUD = 9600;
constexpr uint32_t GPS_STALE_MS = 5000;
constexpr uint8_t INA226_I2C_ADDRESS = 0x44; // Confirmed by live manufacturer/die ID scan on 2026-10-08.
constexpr uint32_t MAX30102_FINGER_IR_MIN = 10000; // Tune after inspecting raw IR.
constexpr uint8_t MAX30102_LED_CURRENT = 0x1F;

// A bare two-wire speaker MUST NOT be connected directly to GPIO2.
// Set true only after adding a suitable driver/amplifier with a 3.3 V logic input.
// false leaves GPIO2 as an input, with no internal pull-up or tone output.
constexpr bool SOUND_DRIVER_CONNECTED = false;
constexpr uint8_t DISPLAY_ROTATION = 1; // 90 degrees clockwise from the original orientation; user confirmed direction.
constexpr bool DISPLAY_INVERT = true;  // GC9A01A default for typical round panels
constexpr uint32_t DISPLAY_SPI_HZ = 2000000; // Slower transfer for the assembled watch's jumper wiring.

// ESP32 supports 2.4 GHz Wi-Fi only.
constexpr char WIFI_SSID[] = "";
constexpr char WIFI_PASSWORD[] = "";
constexpr char INFLUX_URL[] = "";
constexpr char INFLUX_ORG[] = "";
constexpr char INFLUX_BUCKET[] = "";
constexpr char INFLUX_TOKEN[] = "";
constexpr uint32_t INFLUX_INTERVAL_MS = 15000;

// Local MQTT fallback. HiveMQ settings are in cloud_private.h.
// MQTT sends live JSON to Node-RED. Leave MQTT_HOST empty to disable it.
constexpr char MQTT_HOST[] = "";
constexpr uint16_t MQTT_PORT = 1883;
constexpr char MQTT_USER[] = "";
constexpr char MQTT_PASSWORD[] = "";
constexpr char MQTT_TOPIC[] = "ku/iot/ku_watch/ku-watch-449205d4/env";
constexpr uint32_t MQTT_INTERVAL_MS = 1000;
