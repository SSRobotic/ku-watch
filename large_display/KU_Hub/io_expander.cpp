/**
 * ==========================================================================
 *  io_expander.cpp  -  ไดรเวอร์ TCA9554
 * ==========================================================================
 */

#include "io_expander.h"
#include "board_pins.h"
#include <Wire.h>

namespace {

// ---- รีจิสเตอร์ของ TCA9554 (ดูจาก datasheet) ----
constexpr uint8_t REG_INPUT    = 0x00;  // อ่านสถานะขาจริง
constexpr uint8_t REG_OUTPUT   = 0x01;  // สั่งขาเอาต์พุต
constexpr uint8_t REG_POLARITY = 0x02;  // กลับขั้วสัญญาณอินพุต
constexpr uint8_t REG_CONFIG   = 0x03;  // ทิศทางขา: บิต 1 = อินพุต, 0 = เอาต์พุต

/**
 * ทิศทางขาเริ่มต้น
 *   EXIO5 (บิต4) = IMU_INT2  -> อินพุต
 *   EXIO6 (บิต5) = IMU_INT1  -> อินพุต
 *   EXIO7 (บิต6) = RTC_INT   -> อินพุต
 *   ที่เหลือเป็นเอาต์พุต
 *
 *   0b0111 0000 = 0x70
 */
constexpr uint8_t CONFIG_DEFAULT = 0x70;

/**
 * ค่าเอาต์พุตเริ่มต้นที่ "ปลอดภัย"
 *   EXIO1 LCD_RST = HIGH  (ไม่รีเซ็ตจอ)
 *   EXIO2 TP_RST  = HIGH  (ไม่รีเซ็ตทัช)
 *   EXIO3 LCD_CS  = HIGH  (ไม่เลือกจอ)
 *   EXIO4 SD_CS   = HIGH  (ไม่เลือก SD)  <-- สำคัญ: ต้อง HIGH ตอนยังไม่ใช้
 *   EXIO8 BUZZER  = LOW   (เงียบ)
 *
 *   0b0000 1111 = 0x0F
 */
constexpr uint8_t OUTPUT_DEFAULT = 0x0F;

uint8_t g_outputShadow = OUTPUT_DEFAULT;   // จำค่าที่สั่งไปล่าสุด
bool    g_ready        = false;

/** เขียน 1 ไบต์ลงรีจิสเตอร์ */
bool writeReg(uint8_t reg, uint8_t value) {
    Wire.beginTransmission(ADDR_IO_EXPANDER);
    Wire.write(reg);
    Wire.write(value);
    return (Wire.endTransmission() == 0);
}

/** อ่าน 1 ไบต์จากรีจิสเตอร์ */
bool readReg(uint8_t reg, uint8_t &value) {
    Wire.beginTransmission(ADDR_IO_EXPANDER);
    Wire.write(reg);
    if (Wire.endTransmission(false) != 0) return false;   // repeated start

    if (Wire.requestFrom((int)ADDR_IO_EXPANDER, 1) != 1) return false;
    value = Wire.read();
    return true;
}

/** แปลงหมายเลข EXIO (1..8) เป็นบิตมาสก์ */
inline bool exioToMask(uint8_t exio, uint8_t &mask) {
    if (exio < 1 || exio > 8) return false;
    mask = (uint8_t)(1u << (exio - 1));
    return true;
}

} // anonymous namespace


namespace IOExpander {

bool begin() {
    g_ready = false;

    // 1) ตั้งค่าเอาต์พุตก่อน แล้วค่อยตั้งทิศทาง
    //    ลำดับนี้สำคัญ เพื่อไม่ให้ขากระพริบเป็นค่าขยะตอนเปลี่ยนเป็นเอาต์พุต
    if (!writeReg(REG_OUTPUT, OUTPUT_DEFAULT)) return false;
    if (!writeReg(REG_CONFIG, CONFIG_DEFAULT)) return false;
    if (!writeReg(REG_POLARITY, 0x00))         return false;   // ไม่กลับขั้ว

    g_outputShadow = OUTPUT_DEFAULT;

    // 2) อ่านกลับมาตรวจว่าเขียนติดจริง
    uint8_t cfg = 0;
    if (!readReg(REG_CONFIG, cfg))  return false;
    if (cfg != CONFIG_DEFAULT)      return false;

    g_ready = true;
    return true;
}

bool setPin(uint8_t exio, bool high) {
    if (!g_ready) return false;

    uint8_t mask;
    if (!exioToMask(exio, mask)) return false;

    uint8_t next = g_outputShadow;
    if (high) next |=  mask;
    else      next &= ~mask;

    if (!writeReg(REG_OUTPUT, next)) return false;

    g_outputShadow = next;
    return true;
}

bool readPin(uint8_t exio, bool &value) {
    uint8_t mask;
    if (!exioToMask(exio, mask)) return false;

    uint8_t input = 0;
    if (!readReg(REG_INPUT, input)) return false;

    value = (input & mask) != 0;
    return true;
}

uint8_t outputShadow() {
    return g_outputShadow;
}

bool selfTest() {
    if (!g_ready) return false;

    bool v = false;

    // ทดสอบกับ EXIO_SD_CS -- ปลอดภัยเพราะยังไม่ได้เปิดใช้ SD card
    // สั่ง LOW แล้วอ่านกลับ ต้องได้ LOW
    if (!setPin(EXIO_SD_CS, false))   return false;
    delay(2);
    if (!readPin(EXIO_SD_CS, v))      return false;
    if (v != false)                   return false;

    // สั่ง HIGH แล้วอ่านกลับ ต้องได้ HIGH
    if (!setPin(EXIO_SD_CS, true))    return false;
    delay(2);
    if (!readPin(EXIO_SD_CS, v))      return false;
    if (v != true)                    return false;

    // จบการทดสอบ คืนค่าให้อยู่สถานะปลอดภัย (ไม่เลือก SD)
    return setPin(EXIO_SD_CS, true);
}

} // namespace IOExpander
