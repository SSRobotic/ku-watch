#pragma once
#include <stdint.h>

enum class ButtonEvent { None, Down, Click, Home };
class MenuButton {
  bool raw = false, stable = false, held = false;
  uint32_t changed = 0, began = 0;
public:
  ButtonEvent update(bool down, uint32_t now) {
    if (down != raw) { raw = down; changed = now; }
    if (uint32_t(now - changed) >= 30 && raw != stable) {
      stable = raw;
      if (stable) { began = now; held = false; return ButtonEvent::Down; }
      if (!held) return ButtonEvent::Click;
    }
    if (stable && raw && !held && uint32_t(now - began) >= 700) {
      held = true; return ButtonEvent::Home;
    }
    return ButtonEvent::None;
  }
};

// Used on MAP and ROBOT: defer a single tap to recognize a quick double tap.
class MenuTaps {
  bool pending=false;uint32_t at=0;
public:
  bool click(uint32_t now) {
    if(pending && uint32_t(now-at)<450) {pending=false;return true;}
    pending=true;at=now;return false;
  }
  bool leave(uint32_t now,bool down) {
    if(pending && !down && uint32_t(now-at)>=450) {pending=false;return true;}
    return false;
  }
  void cancel() {pending=false;}
  bool waiting() const {return pending;}
};
