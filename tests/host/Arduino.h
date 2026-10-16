#pragma once
#include <stdint.h>
#include <math.h>
#include <algorithm>
using std::min;
using byte = uint8_t;
unsigned long millis();
constexpr double TWO_PI = 6.2831853071795864769;
inline double radians(double v) { return v * TWO_PI / 360; }
inline double degrees(double v) { return v * 360 / TWO_PI; }
template<class T> T sq(T v) { return v*v; }
struct HostSerial { void println(const char*) {} template<typename... T> void printf(const char*,T...) {} };
extern HostSerial Serial;
