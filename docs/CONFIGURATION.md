# Configuration and security

Run `python tools/initialize_local_config.py` to create missing local headers. Existing files are kept. The watch is initialized with cloud disabled and blank network credentials; no shared production key is distributed.

| Local file | Purpose |
|---|---|
| `include/config.h` | Local defaults copied from the checked-in example |
| `include/cloud_private.h` | Cloud host and watch MQTT credentials |
| `include/espnow_private.h` | Random shared 16-byte link key for the watch/hub pair |
| `config/*.local.json` | Workstation-specific access/configuration |
| `config/ota_tls.local/` | Private certificate/key material |

All these paths are ignored. Runtime settings use Preferences/NVS, so changing configured Wi-Fi, broker and thresholds does not require publishing credentials or rebuilding the code. The local setup portal and serial maintenance commands require physical/local access; inspect the relevant service before use.

Exported Node-RED flows use environment references such as `KU_MQTT_USER`, `KU_MQTT_PASSWORD` and `KU_INFLUX_TOKEN`. Do not paste passwords into the exported JSON. The two devices must share a private ESP-NOW key and use the intended peer addresses; hardware MAC constants in the historical source are device identifiers, not authentication secrets.

Automatic OTA requires a reachable HTTPS server and its trust configuration. The original lab server was on the phone-hotspot LAN. Moving the PC to another network can make that endpoint unreachable even when MQTT remains connected. Configure your own reachable endpoint; do not reuse a capability URL from a device dump.

The private handoff excludes live credentials, private TLS keys, credential-bearing firmware/flash backups and raw personal activity exports. Public CA certificates are included as trust anchors. Before any future public release, repeat credential and media review; private visibility is not a substitute for secret management.

Original evidence is preserved locally. Any repository redaction or portable-path copy is listed by the repository audit and does not turn a failed result into a pass.
