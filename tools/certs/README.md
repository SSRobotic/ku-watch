TLS trust bundle prepared 2026-09-23 from Mozilla's public CA list distributed by curl:
https://curl.se/docs/caextract.html
https://curl.se/ca/cacert.pem

Generator: official Espressif Arduino-ESP32 tag 2.0.17 (Apache-2.0 header in script):
https://github.com/espressif/arduino-esp32/blob/2.0.17/tools/gen_crt_bundle.py

Run `gen_crt_bundle.py --input cacert.pem` in this directory using Python with
cryptography installed to regenerate `x509_crt_bundle` (121 roots, 55,587 bytes).
PlatformIO embeds the bundle in the application, outside activity storage.
The client checks the broker certificate and host name. No insecure TLS fallback.
Update this bundle if the public trust store changes or the broker changes CA.
