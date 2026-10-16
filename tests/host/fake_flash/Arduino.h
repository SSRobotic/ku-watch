#pragma once
#include <stdint.h>
#include <stddef.h>
#include <cstdio>
#include <algorithm>
using std::min;using std::max;
inline uint32_t fakeMillis=0;
inline uint32_t millis(){return fakeMillis;}
inline void yield(){}
struct FakeSerial {template<class...Args>void printf(const char*,Args...) {}};
inline FakeSerial Serial;
