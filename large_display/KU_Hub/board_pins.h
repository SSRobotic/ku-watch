/**
 * ==========================================================================
 *  board_pins.h
 *  ขา / แอดเดรส ทั้งหมดของบอร์ด Waveshare ESP32-S3-Touch-LCD-2.1
 * --------------------------------------------------------------------------
 *  ไฟล์นี้คือ "แหล่งความจริงเดียว" (single source of truth)
 *  ห้าม hardcode เลขขาในไฟล์อื่น ให้ include ไฟล์นี้แล้วใช้ชื่อแทน
 *
 *  ข้อมูลอ้างอิงจากเอกสารทางการของ Waveshare
 * ==========================================================================
 */

#pragma once
#include <stdint.h>

// ==========================================================================
//  I2C  (ขาล็อกตายตัว ใช้เป็น GPIO ธรรมดาไม่ได้)
// ==========================================================================
constexpr int      I2C_SDA_PIN = 15;
constexpr int      I2C_SCL_PIN = 7;
constexpr uint32_t I2C_FREQ_HZ = 400000;   // ถ้าบัสไม่นิ่ง ลดเป็น 100000

// ---- แอดเดรสที่ถูกใช้แล้วบนบัสนี้: 0x15, 0x20, 0x51, 0x6B, 0x7E ----
constexpr uint8_t ADDR_TOUCH_CST820  = 0x15;  // จอสัมผัส
constexpr uint8_t ADDR_IO_EXPANDER   = 0x20;  // TCA9554  <-- คุม SD_CS
constexpr uint8_t ADDR_RTC_PCF85063  = 0x51;  // นาฬิกา   <-- timestamp
constexpr uint8_t ADDR_IMU_QMI8658   = 0x6B;  // IMU 6 แกน

// ==========================================================================
//  EXIO  =  ขาบนชิป TCA9554 (ไม่ใช่ GPIO ของ ESP32!)
// --------------------------------------------------------------------------
//  Waveshare เรียกขาพวกนี้ว่า EXIO1..EXIO8
//  ตรงกับขา P0..P7 ของ TCA9554 คือ EXIO n  ->  บิตที่ (n-1)
//
//  *** SD_CS อยู่ที่ EXIO4 ***  จึงสั่งด้วย digitalWrite() ไม่ได้
//      ต้องสั่งผ่าน I2C ไปที่ TCA9554 เท่านั้น
// ==========================================================================
constexpr uint8_t EXIO_LCD_RST  = 1;   // รีเซ็ตจอ
constexpr uint8_t EXIO_TP_RST   = 2;   // รีเซ็ตทัชสกรีน
constexpr uint8_t EXIO_LCD_CS   = 3;   // Chip Select ของจอ
constexpr uint8_t EXIO_SD_CS    = 4;   // Chip Select ของ SD card  <-- สำคัญ
constexpr uint8_t EXIO_IMU_INT2 = 5;   // อินพุต (ขาสัญญาณจาก IMU)
constexpr uint8_t EXIO_IMU_INT1 = 6;   // อินพุต
constexpr uint8_t EXIO_RTC_INT  = 7;   // อินพุต (ขาแจ้งเตือนจาก RTC)
constexpr uint8_t EXIO_BUZZER   = 8;   // ลำโพงบนบอร์ด

// ==========================================================================
//  SD card (SPI)
// --------------------------------------------------------------------------
//  ระวัง: GPIO1 และ GPIO2 ใช้ร่วมกับจอ (LCD_SDA / LCD_SCL)
//         ลำดับการ init จึงมีผล -> จะจัดการใน Step 3
// ==========================================================================
constexpr int SD_MISO_PIN = 42;
constexpr int SD_MOSI_PIN = 1;
constexpr int SD_SCLK_PIN = 2;
// SD_CS = EXIO_SD_CS (ผ่าน IO expander ไม่ใช่ GPIO)

// ==========================================================================
//  อื่น ๆ
// ==========================================================================
constexpr int BAT_ADC_PIN = 4;    // วัดแรงดันแบตเตอรี่

constexpr int LCD_BL_PIN=6,LCD_SPI_SCLK=2,LCD_SPI_MOSI=1,TOUCH_INT_PIN=16;
constexpr int LCD_HSYNC=38,LCD_VSYNC=39,LCD_DE=40,LCD_PCLK=41;
constexpr int LCD_DATA_PINS[16]={5,45,48,47,21,14,13,12,11,10,9,46,3,8,18,17};
