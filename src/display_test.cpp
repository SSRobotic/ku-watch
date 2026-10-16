#include <Arduino.h>
#include <Adafruit_GC9A01A.h>
#include <SPI.h>
#include "config.h"

// Deliberately independent of the watch's framebuffer, sensors and button code.
// Uses the exact agreed GPIO assignments and a much slower SPI clock.
Adafruit_GC9A01A lcd(&SPI, Pin::DC, Pin::CS, Pin::RST);
static unsigned stage = 0;
static uint32_t due = 0;
static const char *names[] = {"RED", "GREEN", "BLUE", "BLACK", "WHITE", "PATTERN"};
static const uint16_t colors[] = {0xf800,0x07e0,0x001f,0x0000,0xffff};

void show() {
  Serial.printf("DISPLAY TEST: %s; SPI 500000; SCK%d MOSI%d CS%d DC%d RST%d\n",
    names[stage],Pin::SCK,Pin::MOSI,Pin::CS,Pin::DC,Pin::RST);
  if(stage < 5) lcd.fillScreen(colors[stage]);
  else {
    lcd.fillScreen(0);
    lcd.fillRect(35,85,55,70,0xf800);
    lcd.fillRect(92,85,55,70,0x07e0);
    lcd.fillRect(149,85,55,70,0x001f);
    lcd.setTextColor(0xffff); lcd.setTextSize(2);
    lcd.setCursor(54,51); lcd.print("GC9A01 TEST");
    lcd.setCursor(48,177); lcd.print("SPI 500 KHZ");
    lcd.drawCircle(120,120,110,0xffff);
  }
  due = millis() + 3000;
}
void setup() {
  pinMode(Pin::SOUND,INPUT);
  pinMode(Pin::BUTTON,INPUT_PULLUP);
  Serial.begin(115200);
  pinMode(Pin::CS,OUTPUT); digitalWrite(Pin::CS,HIGH);
  // Allow the LCD supply to settle, then the driver performs hardware reset.
  delay(300);
  SPI.begin(Pin::SCK,-1,Pin::MOSI,Pin::CS);
  lcd.begin(500000); lcd.setRotation(0); lcd.invertDisplay(true);
  show();
}
void loop() {
  if(int32_t(millis()-due)>=0) { stage=(stage+1)%6; show(); }
  while(Serial.available()) {
    char c=Serial.read();
    if(c=='?') Serial.printf("ALIVE: display_test stage=%s; pixel visibility requires observation\n",names[stage]);
  }
  delay(2);
}
