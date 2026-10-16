# Third-party components and attribution

Project ownership applies to the original KU Watch integration, not to dependencies or vendor designs.
Dependency versions are declared in `platformio.ini`; their original license notices must accompany any redistribution where required.

| Component | Use | Upstream |
|---|---|---|
| Arduino-ESP32 / Espressif | ESP32 firmware runtime, networking and display interfaces | https://github.com/espressif/arduino-esp32 |
| Adafruit GC9A01A, GFX and BusIO | Small display driver and graphics | https://github.com/adafruit/Adafruit_GC9A01A |
| Bosch BME68x and BSEC2 | Environmental sensing and air-quality estimation | https://github.com/boschsensortec/Bosch-BSEC2-Library |
| SparkFun MAX3010x and Maxim reference algorithm | Optical sensor driver and SpO2 calculation | https://github.com/sparkfun/SparkFun_MAX3010x_Sensor_Library |
| RF MAX30102 reference | Method reference for optical periodicity and correlation checks; KU Watch implementation is in `include/ppg_period.h` | https://github.com/aromring/MAX30102_by_RF |
| TinyGPSPlus | NMEA parsing | https://github.com/mikalhart/TinyGPSPlus |
| PubSubClient | MQTT support | https://github.com/knolleary/pubsubclient |
| Waveshare ESP32-S3-Touch-LCD-2.1 | Hub board and vendor interface reference | https://www.waveshare.com/wiki/ESP32-S3-Touch-LCD-2.1 |
| OpenStreetMap contributors | Geographic source data used by map tooling/assets | https://www.openstreetmap.org/copyright |
| Node-RED, FlowFuse Dashboard, InfluxDB, Grafana | External backend services and dashboards | https://nodered.org/ ; https://dashboard.flowfuse.com/ ; https://www.influxdata.com/ ; https://grafana.com/ |

Bosch BSEC2 includes separately licensed binary components. This repository references the dependency; it does not relicense that library. Service names and university marks identify the systems used and do not imply vendor or institutional endorsement.
