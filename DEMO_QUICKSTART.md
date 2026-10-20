# Running the KU Watch demonstration

## View the final submission offline

Open submission/final-2026-10-20/START_HERE.html, or download the ZIP in the private final release and extract it first. OPEN_SUBMISSION.cmd opens the same page on Windows.

This package includes a six-minute MP4, slides, the original and checked requirements, photographs and an FR-01 to FR-08 evidence desk. Saved videos are labeled as recordings; playback does not establish a current live connection.

OPEN_EVIDENCE.cmd at the repository root opens the evidence desk directly. Every FR row has a source-evidence button. Projection view makes the selected result easier to show on a large screen.

## Run the configured workstation

Connect the watch and hub, enable their configured Wi-Fi connection and keep this computer connected to the internet. Run RUN_DEMO.cmd. The launcher opens the existing local backend, checks for fresh MQTT and database records, and opens the Node-RED and Grafana dashboards when their services are ready.

Healthy running services are reused. The launcher reports waiting states when no fresh device data is available. It does not generate readings or count saved/backfilled messages as current live readings.

The local installations, service paths and private configuration are required. See docs/BUILD_AND_SETUP.md for setup on another computer. The portable offline submission needs none of these services.

Closing the launcher closes its observer, while the running services and independent soak collector remain active.
