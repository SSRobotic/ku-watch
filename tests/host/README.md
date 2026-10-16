# Sensor regression checks

Large-display hub (2026-10-08): portable UI/control checks exercise stale-data
suppression, recording clock gates, limits, one-shot touch hold/release (including
CST820 zero-coordinate release), drag cancellation and I2C failure. Version 1.0.3
also checks six rapid taps with queued 4 ms samples, late acquisition of a
navigation target, and overflow cancellation until a stable release. The RTC
checks compile the adapted production PCF85063 driver against a register-level
I2C double and cover calendar/BCD/OS/STOP/12-hour validation plus failure recovery.
These host checks do not prove physical screen appearance or radio pairing.

```powershell
& 'output/host_test_tools/ziglang/zig.exe' c++ -std=c++17 -O2 -Iinclude tests/host/hub.cpp -o output/hub_host_tests.exe
& 'output/hub_host_tests.exe'
& 'output/host_test_tools/ziglang/zig.exe' c++ -std=c++17 -O2 -Itests/host/rtc_fake tests/host/hub_rtc.cpp -o output/hub_rtc_tests.exe
& 'output/hub_rtc_tests.exe'
```

Robot companion (2026-10-08, firmware 1.7.1): 975 host checks exercise the real growth/care
model, CRC restore, no repeated activity credit, short-session accumulation,
food depletion, once-per-day rewards, calendar rollback and level thresholds.
All 10 poses/phases are rendered on all 11 pages. Speech toggling leaves every
pixel below the reserved top band identical. ROBOT double-tap timing, hold
cancellation and wraparound are checked. GPS/map tests also reject weak or
unknown HDOP, stale positions and too few satellites (4,328 sensor / 38 map checks).
Synthetic evolution previews
are host-only and are not injected into watch XP, GPS, MQTT or activity files.

```powershell
& 'output/host_test_tools/ziglang/zig.exe' c++ -std=c++17 -O2 -Iinclude tests/host/robot.cpp -o output/robot_host_tests.exe
& 'output/robot_host_tests.exe'
```

Map regression checks (2026-10-08) compile the production pack validator,
coordinate projection, clipping, trail ring and screen renderer. They cover
damaged CRCs/counts/offsets, missing/stale GPS marker suppression, coverage,
dateline/polar coordinates, gaps and capacity, and render the real Bangkhen pack.

```powershell
& 'output/host_test_tools/ziglang/zig.exe' c++ -std=c++17 -O2 -Iinclude tests/host/maps.cpp -o output/map_host_tests.exe
& 'output/map_host_tests.exe' output/maps/ku_bangkhen.kum
py -m unittest discover -s tests -p test_map_prepare.py
```

These do not verify an outdoor GPS fix or a real walking route. The
position_demo preview is synthetic host input and is never sent to the watch.

Map selection firmware1.7.2: 65 checks cover CRC-protected saved area/mode,
restoring last area when GPS is absent, manual selection resisting auto-follow,
three-choice cycle, missing areas, corrupt records and button tap/hold timing.
The map renderer has 40 checks including manual other-area preview without an
invented wearer marker. Live NVS/board reboot results are in
`output/map_selection_live_20261008.log`.

```powershell
& 'output/host_test_tools/ziglang/zig.exe' c++ -std=c++17 -O2 -Iinclude tests/host/map_selection.cpp -o output/map_selection_host_tests.exe
& 'output/map_selection_host_tests.exe'
```

These tests compile the production pulse detector, FIFO reader and GPS receiver
on a Windows host. The GPS parser is the actual pinned TinyGPSPlus 1.1.0 library.
Arduino time, I2C transfers and MAX30102 initialization are simulated; this does
not verify physical wiring, optical signal quality or satellite reception.

From the project root, after PlatformIO has installed the dependencies:

```powershell
& ./output/host_test_tools/ziglang/zig.exe c++ -std=c++17 -O1 -DARDUINO=10819 -Itests/host -Iinclude -I.pio/libdeps/display_first/TinyGPSPlus/src '-I.pio/libdeps/display_first/SparkFun MAX3010x Pulse and Proximity Sensor Library/src' tests/host/sensors.cpp .pio/libdeps/display_first/TinyGPSPlus/src/TinyGPS++.cpp '.pio/libdeps/display_first/SparkFun MAX3010x Pulse and Proximity Sensor Library/src/spo2_algorithm.cpp' -o output/sensor_host_tests.exe
& ./output/sensor_host_tests.exe
& ./output/host_test_tools/ziglang/zig.exe c++ -std=c++17 -O1 -Itests/host -Iinclude -I.pio/libdeps/display_first/bsec2/src tests/host/environment.cpp -o output/environment_host_tests.exe
& ./output/environment_host_tests.exe
```

The local compiler is Zig 0.13.0, installed only under `output/host_test_tools`.
Another C++17 compiler can use the same sources and include paths. The host must
use a 32-bit `unsigned long` for the Arduino `millis()` wraparound check.

Checks cover 45/60/90/120/150 BPM synthetic signals; no-finger, saturation and
flat-signal resets; FIFO bursts larger than the library's software ring;
overflow, delayed reads, disconnect/reconnect and no-data timeout; GP/GN/GB
NMEA, checksum rejection, no-fix status, zero and negative coordinates,
staleness and timer rollover. PPM previews render the production screen code
with simulated values.

Additional checks cover the MAX30102 overflow counter remaining latched until
a complete FIFO sample is popped, plus pre-fix GSV data, complete message groups,
BD/GB aliases, combined GN reports, checksum rejection, omitted SNR fields and
GSV timeout. Missing fields must not reuse an older satellite's signal strength.

Validation on 2026-09-23: host checks passed; PlatformIO `display_first`,
`max30102_test` and `gps_test` builds passed. After the later live-display
changes, 436 host checks and the main/GPS builds passed. Main firmware was
uploaded and hash-verified on COM15. Serial confirmed MAX30102 live samples
and GPS GSV/received-byte reporting; the GPS still had no position fix.

Walking recorder 1.2.0: 448 host checks include portable binary format/CRC,
GPS UTC conversion, drift suppression and gap/jump handling. Run
`python tests/test_activity_export.py` with lxml installed for nine exporter
checks including the official Garmin TCX schema, recovery, corrupt transfers,
missing sensor fields and GUI construction. The schema was retrieved from
https://www8.garmin.com/xmlschemas/TrainingCenterDatabasev2.xsd.

Live validation evidence is in `output/activity_hardware_validation.json`:
start/stop/download passed, a stopped file survived reboot byte-for-byte,
and an interrupted recording exported successfully with recovery noted.
Both board tests lacked a GPS fix and valid BPM samples, so these tests do
not claim real outdoor track accuracy or moving heart-rate accuracy.

Version 1.5.0 (2026-10-02): 1,148 sensor checks also exercise the real Maxim
SpO2 algorithm with paired optical samples, two-window readiness, flat and
opposite-phase signals, inconsistent BPM, clipping, plus the INA226 identity,
bus-only configuration, conversion-ready flag, invalid voltage and reconnect.
Battery interpolation is checked for bounds and monotonicity. The 19 separate
environment checks use a BSEC/Preferences boundary double to verify warm-up,
accuracy gates, missing fields, stale data, errors and calibration recovery.
They do not validate the proprietary BSEC estimator on a physical sensor.
No simulated samples are sent to MQTT or written to InfluxDB.

Both PlatformIO `display_first` and `max30102_test` builds pass. Version 1.5.0
has not been uploaded because the Super Mini was absent from the USB port list.

2026-10-09: battery_alert.cpp checks ≤20% warning, ≥22% recovery, invalid input
WAITING and all-page warning bounds. Influx flow validation checks readiness
and safe firmware strings. The append-only telemetry dictionary passes 5,116
codec/CRC/ACK checks after adding firmware and battery alert fields.
