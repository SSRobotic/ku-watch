# Architecture and data flow

## Watch node

`src/main.cpp` coordinates the sensor, UI and service modules. `include/pulse_sensor.h` drains real MAX30102 FIFO samples. `ppg_period.h` estimates the optical period over a fresh four-second window after detrending, with agreement checks on both optical channels. `spo2_tracker.h` applies signal quality, perfusion and consecutive-window checks before publishing an estimate. Invalid or stale estimates are cleared.

`environment_sensor.h` delegates BME680 heater scheduling and air-quality processing to BSEC2 at its nominal three-second cadence. IAQ availability depends on warm-up and accuracy status. The UI preserves unavailable states. INA226 measures battery voltage; displayed percentage is an uncalibrated estimate, not coulomb counting.

Version 2.0.15 adds a PSRAM-backed previous-frame cache. The display driver compares eight-row image strips exactly and sends changed strips. Page transitions, resets and alert tests invalidate the cache for a full refresh. Without the optional cache, the firmware uses full frames. The prototype SPI clock remains 2 MHz.

## Companion hub

`large_display/KU_Hub/KU_Hub.ino` receives signed, sequenced ESP-NOW messages and sends acknowledged navigation commands back. It integrates the touch screen, PCF85063 RTC and MicroSD CSV logger. The watch and hub are distinct firmware targets; their flash sizes, display hardware and build configurations differ.

The original requirements named QMI8658 on the sensing side. The assembled watch uses the GY-51 motion module; the hub carries its own QMI8658. The user reported instructor approval of the hardware substitutions. The hub provides MicroSD logging while the small watch uses flash buffering.

## Network and persistence

1. Sensor readings are captured with device timestamps and validity flags.
2. A bounded watch flash journal retains unsent telemetry.
3. The watch sends JSON to `ku/iot/<group>/<device>/env` using MQTT QoS 1 and status/LWT reporting.
4. Node-RED routes current readings, offline replay and isolated test inputs appropriately.
5. InfluxDB stores captured measurements; Grafana queries the resulting time series.

MQTT PUBACK confirms broker delivery, not database persistence. Sequence checks and a database ID audit are required to claim complete storage. Receiver arrival gaps also do not directly measure the physical device screen refresh rate.

The checked backend uses Node-RED on localhost port 1880, InfluxDB 3 on 8181 and Grafana on 3000. These are the recorded deployment choices, not internet-facing production endpoints.

## Settings and update boundary

Runtime settings use NVS/Preferences. Automatic OTA checks a version manifest on boot and periodically, downloads over HTTPS, checks the image hash, uses the alternate application partition and confirms successful boot. The observed automatic update is documented separately from unperformed power-cut rollback tests. Deployment hostnames, private certificates and capability-bearing URLs are local configuration.
