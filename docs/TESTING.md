# Testing and evidence reproduction

## Host checks

Host tests cover frame-cache invalidation and byte-level changes, alert fixtures, pulse FIFO cadence, optical periodicity, invalid/flat/noisy/inconsistent channels, sensor guards, environment handling, settings/extension behavior and OTA gateway input validation. They do not constitute hardware acceptance.

The recorded `tools/run_fr_host_regressions.py` runner uses a local Zig executable and installed PlatformIO dependency sources. Adapt the compiler path or use a compatible C++17 compiler. **Keep assertions enabled** (`-UNDEBUG`); an optimized compile with `NDEBUG` can otherwise silently skip test assertions.

```powershell
python -m unittest discover -s tests -p test_ota_gateway.py
# Point to your local Zig executable, then run the recorded suites:
$env:KU_ZIG = "C:/path/to/zig.exe"
python tools/run_fr_host_regressions.py
```

The original eight C++ suites plus OTA gateway checks passed with assertions enabled; see the [dated report](../evidence/final-2026-10-16/host-regressions-assertions-enabled.json).

## Hardware observations

`tools/fr01_local_observation.py` observes the small-watch and hub USB diagnostic streams, joins partial serial lines and journals only permitted diagnostic observations. A real continuous minute is required. Device screen cadence is measured locally, independently of MQTT arrival jitter. Version 2.0.15 can complete several frames between polls; bounding completed-frame timestamps provide a conservative interval bound, not invented per-frame timestamps.

MQTT audits use actual unique message IDs, missing/duplicate counts and receive intervals over the declared window. Offline tests require an actual interruption and ID comparison after replay into the database. Do not inject fabricated data into the canonical telemetry topic.

FR-06 intentionally uses separate TEST inputs and a test MQTT topic because the original acceptance procedure allows simulated threshold values. Keep them out of InfluxDB history and the real MQTT soak collector. Screenshot and browser clip context must continue to say simulated input.

The project contains many maintenance and hardware scripts that can change settings, reboot or flash a board. Read their arguments and target guards before execution. Cloning the repository is not authorization to execute every diagnostic script against connected equipment.

## Evidence integrity

`docs/REPOSITORY_MANIFEST.json` lists SHA-256 hashes for the curated import. `evidence/repository-audit.json` records the staging audit. Existing observations remain dated with their original firmware versions, methods and pass/fail outcomes. Imported screenshots retain the full image, without a crop implying unavailable data was present.
