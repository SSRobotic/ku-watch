#pragma once

namespace MapZoom {
// Indices 0..3 retain their existing radio/console meanings.
constexpr unsigned COUNT=6, DEFAULT_INDEX=1;
inline bool valid(unsigned index) { return index<COUNT; }
inline double metersPerPixel(unsigned index) {
  static constexpr double scale[]={2,5,10,20,1,.5};
  return scale[valid(index)?index:DEFAULT_INDEX];
}
// Each hold zooms in: 1000 -> 500 -> 250 -> 100 -> 50 -> 25 metres,
// then wraps. These labels describe the existing 50-pixel scale bar.
inline unsigned next(unsigned index) {
  static constexpr unsigned order[]={4,0,1,2,5,3};
  return valid(index)?order[index]:DEFAULT_INDEX;
}
}
