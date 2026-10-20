# Final presentation submission

Prepared 20 October 2026 for the Final Presentation Submission assignment: presentation slides, a demonstration within the requested 5-7 minute range, and the original requirements with a separate checked copy. This package does not submit anything to Google Classroom automatically.

## Opening instructions

Download the ZIP from the [private final release](https://github.com/SSRobotic/ku-watch/releases/tag/v2.0.15-final-submission), use Windows **Extract All**, then open OPEN_SUBMISSION.cmd or START_HERE.html inside the extracted folder. Do not open the page from a ZIP preview.

The offline pages need a browser. Slides need PowerPoint or a PDF viewer; editable requirements need Word or compatible software. The six-minute H.264 MP4 has on-screen explanations, without synthesized narration.

## File guide

Paths below are relative to [the submission folder](../submission/final-2026-10-20/).

| Path | Contents |
|---|---|
| 01_Presentation/KU_Watch_Final.pptx | 29 editable slides: 20 main, nine reference, three embedded recordings |
| 01_Presentation/KU_Watch_Final.pdf | Slide copy, with video poster frames |
| 02_Demo/KU_Watch_Demo_6min.mp4 | Six-minute hardware, Node-RED, database, Grafana, CSV, alert and OTA demonstration |
| 02_Demo/Original_Clips/ | Nine original source recordings |
| 03_Requirements/Requirements_V2_Original.docx | Unchanged original Requirements Plan V2 |
| 03_Requirements/Requirements_V2_Checked.docx | All 16 original criteria, native checkboxes, observations and evidence paths |
| 04_Evidence/index.html | FR-01 to FR-08 buttons, source JSON/CSV, images, videos and projection view |
| 05_Project_Photos/index.html | Gallery of all 139 original photographs/screenshots |
| 06_Hardware/ | Supplied Rev A drawing and schematic |
| MANIFEST.json and SHA256SUMS.txt | File sizes and SHA-256 values |

## Evidence boundaries

Recordings are identified as development footage or dated test recordings. The six-minute video contains saved live-system recordings; playing it does not connect to a currently running watch. Alert scenarios use explicitly marked simulated inputs permitted by FR-06. Rev A drawings remain historical design records.

All eight functional criteria, NFR-02 and NFR-05 have scoped acceptance. Six NFR criteria remain incomplete: continuous 24-hour operation, full latency qualification, battery endurance, reference calibration, actual-price BOM total and three power-interruption rollback trials.

The saved MQTT snapshot contains 30.32 accumulated hours and an 8.17-hour longest continuous interval. These are receiver observations, separate from battery life and whole-system acceptance. The original failed soak audit is preserved separately.

## Live workstation launcher

The root RUN_DEMO.cmd starts the existing setup and verifies fresh MQTT and database records. It needs the configured services, private local settings and hardware described in [build/setup](BUILD_AND_SETUP.md). Its evidence button falls back to the portable submission folder.

A reviewer can view the submission's saved evidence offline without installing Node.js or the backend.
