# KU Watch

KU Watch is a student IoT project combining a wearable sensor node, a companion touch display and a local dashboard stack. This repository contains the firmware, enclosure records, integration code, original photographs and dated acceptance evidence.

Watch **2.0.15**, hub **1.0.8**. The final submission was assembled on **20 October 2026**; integrated hardware acceptance recordings are dated **16 October 2026**. This repository remains **private**.

![KU Watch prototype and companion display](media/hardware/prototype-in-use-01.jpg)

## Final presentation submission

Download the [final submission ZIP from the private release](https://github.com/SSRobotic/ku-watch/releases/tag/v2.0.15-final-submission). Use Windows **Extract All**, then open OPEN_SUBMISSION.cmd or START_HERE.html. The evidence pages and saved recordings work offline.

- 29-slide PowerPoint: 20 main slides and nine reference slides, with three embedded recordings.
- PDF copy of the slides and a six-minute demonstration video.
- Unchanged original Requirements Plan V2 and a checked copy preserving all 16 criteria.
- Evidence page with a button for each of FR-01 through FR-08.
- 139 original photographs/screenshots, nine original clips and supplied Rev A hardware documents.

The presentation retains the original project's Thai language. Repository engineering documentation is in English. See the [file guide](docs/FINAL_SUBMISSION.md) or [submission folder](submission/final-2026-10-20/).

## Live demonstration

On the configured Windows workstation, RUN_DEMO.cmd opens the existing services and checks for fresh MQTT and database records. It reuses healthy services and does not generate sensor data. OPEN_EVIDENCE.cmd opens the saved evidence independently of device connectivity.

A new computer needs the installations and private local settings described in [build/setup](docs/BUILD_AND_SETUP.md). The final ZIP is the portable option for viewing saved demonstrations without those services.

## Project overview

KU Watch combines a small wearable sensor node with a larger touch display and a local IoT dashboard stack. The watch measures environmental conditions, optical pulse signals, movement, battery voltage and GPS status. Data is shown locally, mirrored to the companion display and sent through authenticated MQTT for storage and visualization.

This repository is maintained as **my KU Watch project under SSRobotics**. It includes the engineering source, design records, development photographs, demonstration recordings and dated test evidence. The original Thai project records are retained as an archive; the main technical documentation is in English.

| Sensor node | Companion hub | Backend |
|---|---|---|
| ESP32-S3 Super Mini; GC9A01 round display; MAX30102; BME680; GY-51 motion module; INA226; ATGM336H GPS | Waveshare ESP32-S3-Touch-LCD-2.1; touch navigation; RTC; MicroSD CSV logging | HiveMQ MQTT; Node-RED; InfluxDB; Grafana |

## What the prototype does

- Displays live environmental, pulse/SpO2, motion, battery and GPS information with explicit unavailable/invalid states.
- Mirrors watch state to a touch-operated hub through an authenticated ESP-NOW protocol.
- Publishes timestamped JSON at a nominal one-second cadence using MQTT QoS 1 and a status/LWT topic.
- Buffers telemetry during network outages and replays captured records after reconnection.
- Records RTC-referenced environmental CSV on the hub MicroSD and supports walking-session export.
- Detects persistent temperature and IAQ threshold crossings and exposes alerts on the device and browser dashboard.
- Stores runtime settings in NVS and supports automatic HTTPS OTA with A/B application partitions.

## System architecture

```mermaid
flowchart LR
    S["MAX30102 · BME680
Motion · INA226 · GPS"] --> W["Watch
ESP32-S3 + GC9A01"]
    W <-->|Authenticated ESP-NOW| H["Touch hub
RTC + MicroSD CSV"]
    W -->|"TLS / MQTT QoS 1"| M[HiveMQ]
    M --> N[Node-RED]
    N --> I[InfluxDB]
    I --> G[Grafana]
    W <--> F["Flash journal
Offline replay"]
    O["HTTPS OTA manifest
Version + SHA-256"] --> W
```

See [architecture and data boundaries](docs/ARCHITECTURE.md) for the distinction between radio delivery, broker acknowledgment and database persistence.

## From design to working prototype

<table>
<tr><td width="50%"><img src="media/development/01-cad.png" alt="Case design comparison"><br><b>Enclosure design</b> — CAD iterations and component fit.</td><td width="50%"><img src="media/development/05-assembly-wide.jpg" alt="Open prototype assembly"><br><b>Hardware integration</b> — wiring, sensor discovery and powered bench tests.</td></tr>
<tr><td><img src="media/development/23-backend-screen.png" alt="Early Node-RED integration"><br><b>First backend</b> — live readings routed into dashboard widgets.</td><td><img src="media/dashboards/session-2026-10-16/Grafana_live_50s.png" alt="Actual Grafana dashboard"><br><b>Integrated system</b> — actual captured trends and diagnostic panels.</td></tr>
</table>

[Browse the complete development story and photographs](docs/PROJECT_JOURNEY.md)

## Measured results

| Test | Recorded result | Scope |
|---|---|---|
| FR-01 sensing and display | **69.704 s** continuously valid pulse/SpO2 window; **24.916 Hz** optical samples; conservative display interval bound **861 ms** | Actual version 2.0.15 hardware observation; fingertip bench test |
| FR-03 MQTT reception | **300 / 300** live records over **300 s**; no missing IDs or disconnects | Latest five-minute run; receiver on home Wi-Fi |
| FR-05 outage recovery | **614.0 s** actual Wi-Fi outage; **852** backfilled IDs; **877** complete database IDs in the checked window | Dated 2.0.9 acceptance evidence retained |
| FR-06 alerts | **2 / 2** scenarios passed; worst observed display **2.95 s**, browser **2.66 s** | Explicitly simulated inputs, as allowed by the requirement |
| FR-08 automatic OTA | **2.0.14 2.0.15**, approximately **88 s**, SHA-256 verified | Automatic Wi-Fi update and user confirmation on both displays |

All eight functional requirements have scoped acceptance evidence. NFR-02 and NFR-05 are also accepted within their recorded scope; six non-functional criteria remain incomplete. **This does not mean that every non-functional requirement is complete.** Battery endurance, calibration, continuous 24-hour operation and power-interruption rollback tests remain separate. The saved snapshot records 30.32 h accumulated MQTT reception and an 8.17 h longest continuous interval. Neither figure establishes continuous 24-hour operation, battery life or a whole-system pass.

The pulse and SpO2 values are experimental estimates. The accepted fingertip test does not establish reliable wrist measurement or clinical accuracy.

[Read the full acceptance matrix, failed attempts and remaining work](docs/VALIDATION.md)

## Watch the demonstrations

<table>
<tr><td width="50%"><a href="media/videos/pulse-demo.mp4"><img src="media/video-posters/pulse-demo.jpg" alt="Pulse demonstration"><br>Pulse values on both displays · 13 s</a></td><td width="50%"><a href="media/videos/grafana-live-60s.mp4"><img src="media/video-posters/grafana-live-60s.jpg" alt="Actual Grafana recording"><br>Grafana values changing over time · 60 s</a></td></tr>
</table>

[All nine clips, with context and duration](docs/DEMONSTRATIONS.md) · [Every captured dashboard panel](docs/DASHBOARD_GALLERY.md)

## Repository guide

| Location | Contents |
|---|---|
| [`src/`](src/) and [`include/`](include/) | Watch firmware and modular services |
| [`large_display/KU_Hub/`](large_display/KU_Hub/) | Companion display firmware |
| [`hardware/`](hardware/) | KiCad sources, drawing and schematic records |
| [`integration/`](integration/) | Credential-free Node-RED and Grafana configuration |
| [`tests/`](tests/) | Host unit tests and integration checks |
| [`tools/`](tools/) | Build, observation, maintenance and evidence tools |
| [`media/`](media/) | Actual project photographs, screenshots and videos |
| [`evidence/`](evidence/) | Dated observations, including failed and partial attempts |
| [`docs/`](docs/) | English engineering documentation and media guides |
| [`archive/`](archive/) | Original project acceptance documents and dated material |

Start with [build and setup](docs/BUILD_AND_SETUP.md), [hardware wiring](docs/HARDWARE.md), [testing](docs/TESTING.md), and [handoff notes](docs/HANDOFF.md). Large original presentations and the verified handoff ZIP are listed in the [private review release](https://github.com/SSRobotic/ku-watch/releases/tag/v2.0.15-private-review).

## Configuration and ownership

The repository contains templates and references, not live credentials, private TLS keys, device flash backups or raw personal activity exports. Follow [configuration and security](docs/CONFIGURATION.md) before compiling for your own devices. Historical maintenance scripts may contain workstation-specific paths and verified device MAC guards; inspect them before reuse.

Copyright (c) 2026 **SSRobotics**. Original project materials are reserved for private review. See [ownership](COPYRIGHT.md) and [third-party notices](THIRD_PARTY_NOTICES.md).
