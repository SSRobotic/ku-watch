# Requirements and acceptance evidence

Evidence cutoff: **16 October 2026**, watch **2.0.15**, hub **1.0.8**. Acceptance is scoped to the recorded run and method. Earlier-version checks remain dated earlier-version evidence.

## Functional requirements

| ID | Requirement / acceptance boundary | Recorded result |
|---|---|---|
| FR-01 | Read optical, motion and environmental sensors; pulse/SpO2 and motion display at least 1 Hz; IAQ nominally every 3 s; operate without error for one minute | Accepted on 2.0.15: 69.704 s continuous valid estimates, 24.916 Hz pulse acquisition, 1.759 Hz motion, 5.321 completed display updates/s, conservative largest frame interval bound 861 ms, 23 BSEC conversions, no FIFO resets or missed quality windows |
| FR-02 | Correct current values/time/battery/connectivity; touch-operated display | Accepted within checked UI scope: user confirmation and dated 11-page checks; both displays physically confirmed on 2.0.15. This is not the separate 300 ms touch-latency proof |
| FR-03 | JSON on canonical topic every second, QoS 1, status/LWT; receive every scheduled message for 5 min | Accepted on 2.0.15: 300 unique live records/300 s, no missing IDs, duplicates or disconnects; max observed receive gap 1782.85 ms. Original receive-gap guard retained |
| FR-04 | RTC-referenced MicroSD CSV every 5 s, readable in Excel with complete rows | Accepted for checked windows: 1,408 rows on 14 Oct; 61 rows over 5 min 1 s on 16 Oct; 26 columns, RTC difference at most 1 s, record spacing 4–6 s. No all-day completeness claim |
| FR-05 | Continue sampling/buffering for 10 min offline and replay backlog automatically | Accepted in dated 2.0.9 run: actual 614.0 s Wi-Fi outage, 852 replayed IDs and complete 877-ID database window. Small-watch flash buffer and hub CSV are distinct storage paths |
| FR-06 | Temperature >35 C or IAQ >150 for 3 readings; alert within 5 s | Accepted using explicitly simulated inputs permitted by the original plan: 2/2 latest 2.0.15 cases; display <=2.951 s, browser <=2.656 s. TEST topic/input stays outside real storage and soak evidence |
| FR-07 | Change Wi-Fi/broker/threshold settings without reflash; persist after reboot | Accepted in dated NVS change/reboot/restore check; canonical topic and original thresholds restored, activity files preserved |
| FR-08 | Automatically check/download a newer firmware on boot/within 24 h; version on screen and status | Accepted: actual automatic HTTPS 2.0.14→2.0.15 update in about 88 s, verified SHA-256 and boot confirmation, MQTT version and user confirmation on both displays |

The original watch-side QMI8658/MicroSD specification was implemented with reported instructor-approved substitutions: GY-51 motion input and flash buffering on the small watch, with MicroSD and QMI8658 on the hub. This approval is user-reported; it is not an independent certification.

## Non-functional requirements

| ID | Original target | Current status |
|---|---|---|
| NFR-01 | Continuous 24 h operation without manual reboot or lock-up | **Incomplete.** 30.32 h accumulated MQTT reception, longest continuous interval 8.17 h in the saved 20 October submission snapshot. Accumulated time is not 24 h continuous operation, battery life or whole-system acceptance |
| NFR-02 | Survive a 10 min network/broker outage and reconnect automatically with backoff | **Accepted in the recorded outage test.** Watch kept running during actual 614 s Wi-Fi interruption and recovered automatically |
| NFR-03 | Online sensor-to-Grafana <=5 s and touch response <=300 ms; 10 timing observations | **Incomplete.** Some query-latency observations exist; full physical sensor-to-painted-browser and quantitative touch boundary are not established |
| NFR-04 | 1000 mAh Li-Po operation >=6 h, measured until 20% | **Not tested.** Bench tests used USB. Portable use and estimated battery percentage do not establish endurance |
| NFR-05 | No confidential credentials in GitHub source; authenticated broker | **Accepted for the audited private repository snapshot.** Actual committed blobs, ignored private paths and recursive release attachments were checked; no known credentials or private keys were found. Authenticated MQTT operation is separately evidenced. The earlier Word checklist is retained unchanged |
| NFR-06 | Temperature within +/-3 C of reference over 10 points; label health values preliminary | Health estimates are labeled experimental. **Calibration incomplete:** no 10-point reference-temperature dataset supplied |
| NFR-07 | Actual complete hardware BOM <=3,000 THB | **Incomplete.** Actual purchase prices have not been filled for a verified total |
| NFR-08 | Modular code, A/B rollback and OTA battery gate; 3 power-cut recovery trials | Modules and A/B OTA are implemented; successful updates observed. **Power-cut acceptance incomplete:** three interruption/rollback trials have not been performed |

The [20 October final submission](FINAL_SUBMISSION.md) preserves the unchanged original Requirements Plan V2 and a checked copy with all original criterion text.

## Evidence entry points

- [Latest sensor result](../evidence/final-2026-10-16/evidence/FR01_20261016T160220Z.json)
- [Latest MQTT five-minute result](../evidence/final-2026-10-16/evidence/mqtt_2.0.15_pc_home_5min.json)
- [Actual outage recovery](../evidence/final-2026-10-16/historical/FR05_NFR02_2.0.9_offline_10min.json)
- [NVS settings persistence](../evidence/final-2026-10-16/historical/FR07_2.0.9_NVS_reboot.json)
- [Latest alert result](../evidence/final-2026-10-16/evidence/FR06_2026-10-16T16-04-02-772Z.json)
- [Automatic OTA to 2.0.15](../evidence/final-2026-10-16/evidence/fr08_auto_update_2.0.15.json)
- [Physical display confirmation](../evidence/final-2026-10-16/evidence/user_visual_confirmation_2.0.15.json)
- [Assertions-enabled host regression report](../evidence/final-2026-10-16/host-regressions-assertions-enabled.json)
- [Original failed soak audit](../evidence/final-2026-10-16/historical/failed_soak_original.json)
- [Original final Word checklist, Thai](../archive/acceptance-thai/KU_Watch_FR_Status_2.0.15_ready15.docx)

- [Actual private repository and release verification](../evidence/repository-upload-verification.json)

## Failed and partial attempts

Earlier receive-gap failures, unstable optical windows, the 2.0.14 display-interval miss, an interrupted/corrupt OTA attempt and its later retry are retained alongside the successful runs. Earlier host harness output with assertions disabled is historical, not valid passing evidence; the accepted regression report explicitly records `-UNDEBUG`.

The final acceptance values are actual measurements. Demonstration photos, videos, software simulations and UI previews cannot substitute for a missing measurement. Continuous monitoring remains an independent process; a dated repository snapshot will not automatically update its results.
