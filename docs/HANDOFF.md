# Private project handoff

The final functional-acceptance handoff is watch 2.0.15 / hub 1.0.8, dated 16 October 2026. This repository brings together the source, original design records, development history, actual media and test evidence under the project owner's GitHub account.

## Review order

1. Read the root README for scope and system structure.
2. Browse the project journey and video index.
3. Check the acceptance matrix against linked dated JSON evidence.
4. Open the original presentations in the private review release. These retain their original Thai language and precede the final firmware acceptance updates; the English matrix is the current technical status guide.
5. Inspect the firmware, hardware and integration directories before reproducing the setup.

## Included

Watch/hub source, host tests, integration exports, design PDFs/KiCad files, full development photographs, captured dashboard panels, nine demonstration clips, original project notes, final Word checklist and previous failed/partial test outcomes. Duplicate files and intermediate slide/render builds are not repeated.

## Kept only on the original workstation

Live passwords/tokens, private keys, complete flash backups, compiled device images containing configuration, raw GPS/activity recordings, running process state, database storage, dependency caches and intermediate build outputs. These are runtime/private data, not missing engineering deliverables. Original local evidence is not deleted or modified by preparing this repository.

## Remaining validation

Continuous 24-hour operation, six-hour battery endurance, reference calibration, full end-to-end/touch latency, actual-price BOM and three power-interruption OTA rollback trials remain open. Continuous MQTT monitoring is independent of this repository import and is not silently stopped by the handoff.

No collaborator invitations, public visibility, Pages site or automatic deployment is enabled by this handoff. Future public release requires a separate owner decision.

## Fresh import checks

The sanitized watch checkout compiled successfully with PlatformIO. All eight host C++ suites and the OTA gateway checks passed again with assertions enabled. These checks did not flash either connected device. See `evidence/private-import-watch-build.json` and `evidence/private-import-host-regressions.json`.
