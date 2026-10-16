#include <cassert>
#include <iostream>
#include "../../large_display/KU_Hub/rtc_pcf85063.cpp"
int main(){
  RtcTime leap{2024,2,29,4,23,59,59},out{};
  assert(Rtc::begin());assert(!Rtc::isTimeValid());assert(Rtc::write(leap));
  assert(Wire.registers[0]==1);assert(Rtc::read(out));assert(out.year==2024 && out.month==2 && out.day==29);
  leap.year=2025;assert(!Rtc::write(leap));leap.year=2024;
  Wire.registers[4]|=0x80;assert(!Rtc::read(out));Wire.registers[4]&=0x7f;
  Wire.registers[0]=0x21;assert(Rtc::begin());assert(Wire.registers[0]==0x21);assert(!Rtc::read(out));Wire.registers[0]=1;
  Wire.registers[5]=0x1a;assert(!Rtc::read(out));Wire.registers[5]=0x60;assert(!Rtc::read(out));Wire.registers[5]=0x59;
  Wire.registers[0]=3;assert(!Rtc::read(out));Wire.registers[0]=1;
  Wire.shortRead=true;assert(!Rtc::read(out));Wire.shortRead=false;
  Wire.failWrite=Wire.writes+2;assert(!Rtc::write(leap));assert(Wire.registers[0]==1); // failed calendar write must resume RTC
  Wire.failWrite=0;assert(Rtc::write(leap));assert(Rtc::read(out));
  Wire.connected=false;assert(!Rtc::begin());assert(!Rtc::write(leap));assert(!Rtc::read(out));
  std::cout<<"Production PCF85063 leap/calendar/BCD/OS/STOP/12h/short-read/NACK and failed-write resume checks passed\n";
}
