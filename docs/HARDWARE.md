# Hardware and wiring

## Assembled devices

| Item | Role |
|---|---|
| ESP32-S3 Super Mini | Small watch controller; firmware target has 4 MB flash |
| GC9A01 round 1.28-inch display | Small watch SPI display |
| MAX30102 | Red/IR optical measurements for experimental pulse and SpO2 estimates |
| BME680 | Temperature, humidity, pressure and gas; BSEC2 IAQ processing |
| GY-51 motion module | Assembled watch motion input; approved substitution reported by the user |
| INA226, address 0x44 | Battery voltage measurement |
| ATGM336H GPS/BeiDou | UART NMEA receiver |
| Waveshare ESP32-S3-Touch-LCD-2.1 | Larger touch display, RTC and MicroSD logging hub; 16 MB build target |
| Li-Po 1S, 1000 mAh | Portable power source; endurance not validated |

## Small watch connections

| Signal | GPIO / connection |
|---|---|
| Display SCK / MOSI | 10 / 11 |
| Display CS / DC / reset | 6 / 7 / 5 |
| Shared I2C SDA / SCL | 8 / 9 |
| GPS TX → watch RX | 12 |
| GPS RX ← watch TX | 13 |
| Navigation button | 4 to GND, input pull-up |
| Reserved sound-driver signal | 2; driver disabled in the recorded assembly |

These are GPIO numbers, not connector positions. Display SCL/SDA labels refer to SPI, not sensor I2C. MAX30102 uses address 0x57, BME680 normally 0x76 with 0x77 fallback, and INA226 was detected at 0x44.

Use a common ground and the voltage appropriate to the actual module. A bare speaker must not connect directly to a GPIO. INA226 is a measurement module, not a battery charger. Its shunt terminals must not be placed directly across battery positive and negative. The battery's third wire has not been established in this handoff; do not infer its function from color. USB-powered operation is the bench-test mode. A regulated portable-power path must be checked against the assembled wiring.

## Design records

- [KiCad project](../hardware/KU_Watch/KU_Watch.kicad_pro)
- [Drawing PDF](../hardware/design-records/KU_Watch_Drawing.PDF)
- [Schematic PDF](../hardware/design-records/KU_Watch_Schematic.pdf)
- [Drawing preview](../hardware/design-records/drawing.png)
- [Schematic preview](../hardware/design-records/schematic.png)

The drawing, schematic and development photos document different stages. Resolve differences against the current pin constants and physical assembly before reproducing the hardware. They are not a manufacturing qualification.
