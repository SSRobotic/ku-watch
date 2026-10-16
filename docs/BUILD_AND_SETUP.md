# Build and setup

## Recorded toolchain

The watch uses PlatformIO `espressif32@7.1.1`, Arduino framework, board `esp32-s3-devkitc-1`, C++17, 4 MB flash and the custom `partitions.csv`. `platformio.ini` is the authoritative dependency list. Some dependency references are floating (SparkFun Git and PubSubClient caret range); the exact installed dependency resolution is recorded in `evidence/dependency-lock-2026-10-16.json` when available. A future rebuild should use the recorded versions/commit before comparison with hardware evidence.

The hub uses Arduino CLI with a distinct ESP32-S3 16 MB target. Its recorded command is documented below. Existing hardware evidence does not imply that a newly resolved dependency tree has already been tested.

## Watch build

```powershell
git clone https://github.com/SSRobotic/ku-watch.git
cd ku-watch
python tools/initialize_local_config.py
pio run -e display_first
```

The initializer creates only ignored local headers. It never starts a network service or flashes a device. Configure Wi-Fi/MQTT through your local settings/NVS workflow; see [configuration](CONFIGURATION.md). The generated ESP-NOW key is random and must be shared by the two firmware builds. Set the intended peer MAC addresses for your own hardware.

To flash the small watch after verifying the physical target:

```powershell
pio run -e display_first -t upload --upload-port COM15
pio device monitor --port COM15 --baud 115200
```

`COM15` is the recorded workstation port, not a universal device address. Upload only to the small controller. Other environments (`display_test`, `max30102_test`, `gy51_test`, `gps_test`, `button_test`, `espnow_bridge_test`) are diagnostic programs and replace the normal watch application when flashed.

## Hub build

Install Arduino CLI and the ESP32 Arduino board core used by the recorded deployment. The local installed version is listed in the dependency snapshot where detected. Use:

```powershell
arduino-cli compile --jobs 4 --fqbn "esp32:esp32:esp32s3:FlashSize=16M,PSRAM=opi,FlashMode=qio,USBMode=hwcdc,CDCOnBoot=cdc,PartitionScheme=app3M_fat9M_16MB" --build-property "compiler.cpp.extra_flags=-I$((Resolve-Path include).Path)" large_display/KU_Hub
```

`tools/build_large.py` records the original workstation wrapper. Its upload path intentionally requires the known hub MAC and an existing complete flash backup. A new machine must adapt paths and verify its own device identity. Do not remove target guards simply to make an upload proceed.

## Backend

1. Use your existing or new authenticated MQTT broker with TLS. Create separate publish and read accounts with topic-scoped access.
2. Import `integration/node-red/ku-watch-cloud-flow.json`. Install the dashboard node types referenced by that flow. Supply MQTT and Influx credentials through local environment variables/settings; none are provided here.
3. Review flow references and attach the imported project nodes to your own existing dashboard page/configuration. This exported project fragment is not a complete export of another user's Node-RED installation.
4. Configure the InfluxDB database and URL expected by `integration/node-red/to_influx.js`. Confirm an actual write and query, rather than inferring success from MQTT alone.
5. Import `integration/grafana/ku-watch-live.json` and bind its data source to your InfluxDB instance. Historical dashboard text remains in its original UI language.

Original launch/maintenance scripts preserve the original Windows deployment paths and existing database. Review and adapt them before use; they are not an unattended installer. No backend services are deployed by cloning this repository.
