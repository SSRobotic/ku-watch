/**
 * ==========================================================================
 *  rtc_pcf85063.cpp  -  ไดรเวอร์นาฬิกา PCF85063
 * ==========================================================================
 */

#include "rtc_pcf85063.h"
#include "board_pins.h"
#include <Wire.h>
#include <string.h>
#include <stdlib.h>

namespace {

// ---- รีจิสเตอร์ของ PCF85063 (จาก datasheet) ----
constexpr uint8_t REG_CONTROL_1 = 0x00;
constexpr uint8_t REG_CONTROL_2 = 0x01;
constexpr uint8_t REG_SECONDS   = 0x04;   // บิต7 = OS (Oscillator Stop)
constexpr uint8_t REG_MINUTES   = 0x05;
constexpr uint8_t REG_HOURS     = 0x06;
constexpr uint8_t REG_DAYS      = 0x07;
constexpr uint8_t REG_WEEKDAYS  = 0x08;
constexpr uint8_t REG_MONTHS    = 0x09;
constexpr uint8_t REG_YEARS     = 0x0A;

// ---- บิตใน Control_1 ----
// Waveshare's crystal uses CAP_SEL=1 (12.5 pF), as in its official driver.
constexpr uint8_t CTRL1_STOP   = 0x21;
constexpr uint8_t CTRL1_RUN    = 0x01;

// ---- บิตใน Seconds ----
constexpr uint8_t SECONDS_OS   = 0x80;   // 1 = เวลาไม่น่าเชื่อถือ (เคยไฟดับ)

/** แปลง BCD -> เลขฐานสิบ  เช่น 0x25 -> 25 */
inline uint8_t bcd2dec(uint8_t v) { return (uint8_t)((v >> 4) * 10 + (v & 0x0F)); }

/** แปลงเลขฐานสิบ -> BCD  เช่น 25 -> 0x25 */
inline uint8_t dec2bcd(uint8_t v) { return (uint8_t)(((v / 10) << 4) | (v % 10)); }

bool writeReg(uint8_t reg, uint8_t value) {
    Wire.beginTransmission(ADDR_RTC_PCF85063);
    Wire.write(reg);
    Wire.write(value);
    return (Wire.endTransmission() == 0);
}

bool readBytes(uint8_t reg, uint8_t *buf, uint8_t len) {
    Wire.beginTransmission(ADDR_RTC_PCF85063);
    Wire.write(reg);
    if (Wire.endTransmission(false) != 0) return false;   // repeated start

    if (Wire.requestFrom((int)ADDR_RTC_PCF85063, (int)len) != len) return false;
    for (uint8_t i = 0; i < len; i++) buf[i] = Wire.read();
    return true;
}

/**
 * คำนวณวันในสัปดาห์จากวันที่ (Sakamoto's algorithm)
 * คืนค่า 0 = อาทิตย์ .. 6 = เสาร์
 */
uint8_t calcWeekday(uint16_t y, uint8_t m, uint8_t d) {
    static const int t[] = {0, 3, 2, 5, 0, 3, 5, 1, 4, 6, 2, 4};
    if (m < 3) y -= 1;
    return (uint8_t)((y + y / 4 - y / 100 + y / 400 + t[m - 1] + d) % 7);
}

} // anonymous namespace


namespace Rtc {

bool begin() {
    // Detection must not turn a stopped or invalid clock into trusted time.
    uint8_t control=0;return readBytes(REG_CONTROL_1,&control,1);
}

bool isTimeValid() {
    RtcTime t; return read(t);
}

bool validDate(const RtcTime& t) {
    if(t.year<2024 || t.year>2099 || t.month<1 || t.month>12 || t.hour>23 || t.minute>59 || t.second>59 || t.weekday>6)return false;
    static const uint8_t days[]={31,28,31,30,31,30,31,31,30,31,30,31};
    unsigned limit=days[t.month-1]+(t.month==2 && t.year%4==0);
    return t.day>=1 && t.day<=limit;
}

bool read(RtcTime &t) {
    uint8_t buf[7] = {0};
    uint8_t control=0;
    if(!readBytes(REG_CONTROL_1,&control,1) || (control & 0x22))return false;
    if (!readBytes(REG_SECONDS, buf, 7)) return false;
    if(buf[0]&SECONDS_OS)return false;
    const uint8_t masks[]={0x7f,0x7f,0x3f,0x3f,0x07,0x1f,0xff};
    for(unsigned i=0;i<7;++i) {uint8_t b=buf[i]&masks[i];if((b&15)>9 || (b>>4)>9)return false;}

    t.second  = bcd2dec(buf[0] & 0x7F);   // ตัดบิต OS ทิ้ง
    t.minute  = bcd2dec(buf[1] & 0x7F);
    t.hour    = bcd2dec(buf[2] & 0x3F);   // โหมด 24 ชม. ใช้ 6 บิตล่าง
    t.day     = bcd2dec(buf[3] & 0x3F);
    t.weekday = (uint8_t)(buf[4] & 0x07);
    t.month   = bcd2dec(buf[5] & 0x1F);
    t.year    = (uint16_t)(2000 + bcd2dec(buf[6]));   // ชิปเก็บแค่ 2 หลัก

    return validDate(t);
}

bool write(const RtcTime &t) {
    if(!validDate(t))return false;
    // 1) หยุดนาฬิกาก่อนเขียน กันค่าเปลี่ยนกลางคัน
    if (!writeReg(REG_CONTROL_1, CTRL1_STOP)) return false;

    // 2) เขียนค่าทั้ง 7 รีจิสเตอร์รวดเดียว
    //    การเขียนวินาทีโดยให้บิต7 = 0 จะล้างแฟล็ก OS ไปในตัว
    Wire.beginTransmission(ADDR_RTC_PCF85063);
    Wire.write(REG_SECONDS);
    Wire.write(dec2bcd(t.second) & 0x7F);
    Wire.write(dec2bcd(t.minute));
    Wire.write(dec2bcd(t.hour));
    Wire.write(dec2bcd(t.day));
    Wire.write(t.weekday & 0x07);
    Wire.write(dec2bcd(t.month));
    Wire.write(dec2bcd((uint8_t)(t.year % 100)));
    bool written=Wire.endTransmission()==0;

    // 3) ปล่อยให้นาฬิกาเดินต่อ
    bool resumed=writeReg(REG_CONTROL_1, CTRL1_RUN);
    return written && resumed;
}

bool setFromBuildTime() {
    // __DATE__ มีรูปแบบ "Sep 19 2026"
    // __TIME__ มีรูปแบบ "17:35:42"
    const char *d = __DATE__;
    const char *tm = __TIME__;

    static const char months[] = "JanFebMarAprMayJunJulAugSepOctNovDec";

    char monStr[4] = {d[0], d[1], d[2], '\0'};
    uint8_t month = 0;
    for (uint8_t i = 0; i < 12; i++) {
        if (strncmp(monStr, months + i * 3, 3) == 0) { month = i + 1; break; }
    }
    if (month == 0) return false;

    RtcTime t;
    t.year   = (uint16_t)atoi(d + 7);
    t.month  = month;
    t.day    = (uint8_t)atoi(d + 4);
    t.hour   = (uint8_t)atoi(tm);
    t.minute = (uint8_t)atoi(tm + 3);
    t.second = (uint8_t)atoi(tm + 6);
    t.weekday = calcWeekday(t.year, t.month, t.day);

    return write(t);
}

String toISO8601(const RtcTime &t) {
    char buf[24];
    snprintf(buf, sizeof(buf), "%04u-%02u-%02uT%02u:%02u:%02u",
             t.year, t.month, t.day, t.hour, t.minute, t.second);
    return String(buf);
}

const char* weekdayName(uint8_t weekday) {
    static const char *names[] = {
        "อาทิตย์", "จันทร์", "อังคาร", "พุธ", "พฤหัสบดี", "ศุกร์", "เสาร์"
    };
    if (weekday > 6) return "??";
    return names[weekday];
}

} // namespace Rtc
