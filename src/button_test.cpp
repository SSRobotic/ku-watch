#include <Arduino.h>
#include "config.h"

static bool lastPressed = false;

void setup() {
  Serial.begin(115200);
  pinMode(Pin::BUTTON, INPUT_PULLUP);

  delay(300);
  bool pressed = digitalRead(Pin::BUTTON) == LOW;
  lastPressed = pressed;

  Serial.println();
  Serial.printf("BUTTON TEST: GPIO%d, INPUT_PULLUP\n", Pin::BUTTON);
  Serial.println("Wiring: GPIO4 <-> switch <-> GND");
  Serial.printf("Initial reading: %d (%s)\n", pressed ? 0 : 1,
    pressed ? "PRESSED" : "RELEASED");
  Serial.println("Expected: released=1, pressed=0");
}

void loop() {
  static uint32_t changedAt = 0;
  bool pressed = digitalRead(Pin::BUTTON) == LOW;
  uint32_t now = millis();

  if (pressed != lastPressed && uint32_t(now - changedAt) >= 30) {
    changedAt = now;
    lastPressed = pressed;
    Serial.printf("GPIO%d = %d -> %s\n", Pin::BUTTON, pressed ? 0 : 1,
      pressed ? "PRESSED" : "RELEASED");
  }

  delay(1);
}