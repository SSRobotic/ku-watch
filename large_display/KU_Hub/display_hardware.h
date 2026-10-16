#pragma once
#include <Arduino.h>
#include <Wire.h>
#include <driver/spi_master.h>
#include <esp_lcd_panel_rgb.h>
#include <esp_lcd_panel_ops.h>
#include "board_pins.h"
#include "io_expander.h"
#include "lcd_init.h"

class HubDisplay {
  inline static volatile uint32_t touchIrqs=0;
  uint32_t seenIrqs=0;
  static void IRAM_ATTR onTouch();
  spi_device_handle_t spi=nullptr;
  esp_lcd_panel_handle_t panel=nullptr;
  bool transaction(unsigned kind,uint8_t byte) {
    spi_transaction_t t{};t.cmd=kind;t.addr=byte;
    return spi_device_transmit(spi,&t)==ESP_OK;
  }
public:
  bool ready=false,touchReady=false;
  bool releaseCommandBus(){
    if(!ready || !spi)return false;
    if(spi_bus_remove_device(spi)!=ESP_OK)return false;spi=nullptr;
    return spi_bus_free(SPI2_HOST)==ESP_OK;
  }
  uint32_t frames=0,touchErrors=0,touchSamples=0;uint8_t touchGesture=0,touchPoints=0;bool completedTap=false;
  bool begin() {
    pinMode(LCD_BL_PIN,OUTPUT);digitalWrite(LCD_BL_PIN,LOW);
    if(!IOExpander::begin())return false;
    if(!IOExpander::setPin(EXIO_LCD_RST,false))return false;delay(10);
    if(!IOExpander::setPin(EXIO_LCD_RST,true))return false;delay(50);
    spi_bus_config_t bus{};bus.mosi_io_num=LCD_SPI_MOSI;bus.miso_io_num=-1;bus.sclk_io_num=LCD_SPI_SCLK;
    bus.quadwp_io_num=bus.quadhd_io_num=-1;bus.max_transfer_sz=64;
    if(spi_bus_initialize(SPI2_HOST,&bus,SPI_DMA_CH_AUTO)!=ESP_OK)return false;
    spi_device_interface_config_t device{};device.command_bits=1;device.address_bits=8;
    device.clock_speed_hz=40000000;device.spics_io_num=-1;device.queue_size=1;
    if(spi_bus_add_device(SPI2_HOST,&device,&spi)!=ESP_OK)return false;
    if(!IOExpander::setPin(EXIO_LCD_CS,false))return false;
    for(auto step:LCD_INIT) {
      if(step.kind==2)delay(step.value);
      else if(!transaction(step.kind,uint8_t(step.value)))return false;
    }
    if(!IOExpander::setPin(EXIO_LCD_CS,true))return false;
    esp_lcd_rgb_panel_config_t config{};
    config.clk_src=LCD_CLK_SRC_DEFAULT;config.data_width=16;config.bits_per_pixel=16;
    config.num_fbs=2;config.bounce_buffer_size_px=480*10;config.psram_trans_align=64;
    config.hsync_gpio_num=LCD_HSYNC;config.vsync_gpio_num=LCD_VSYNC;config.de_gpio_num=LCD_DE;config.pclk_gpio_num=LCD_PCLK;
    config.disp_gpio_num=-1;for(unsigned i=0;i<16;++i)config.data_gpio_nums[i]=LCD_DATA_PINS[i];
    config.timings.pclk_hz=16000000;config.timings.h_res=config.timings.v_res=480;
    config.timings.hsync_pulse_width=8;config.timings.hsync_back_porch=10;config.timings.hsync_front_porch=50;
    config.timings.vsync_pulse_width=3;config.timings.vsync_back_porch=8;config.timings.vsync_front_porch=8;
    config.flags.fb_in_psram=true;
    if(esp_lcd_new_rgb_panel(&config,&panel)!=ESP_OK || esp_lcd_panel_reset(panel)!=ESP_OK || esp_lcd_panel_init(panel)!=ESP_OK)return false;
    digitalWrite(LCD_BL_PIN,HIGH);ready=true;
    pinMode(TOUCH_INT_PIN,INPUT_PULLUP);IOExpander::setPin(EXIO_TP_RST,false);delay(10);IOExpander::setPin(EXIO_TP_RST,true);delay(50);
    Wire.beginTransmission(ADDR_TOUCH_CST820);Wire.write(0xfe);Wire.write(0xff);touchReady=Wire.endTransmission()==0;
    if(touchReady)attachInterrupt(digitalPinToInterrupt(TOUCH_INT_PIN),onTouch,FALLING);
    return true;
  }
  bool draw(const uint16_t* pixels) {
    if(!ready || esp_lcd_panel_draw_bitmap(panel,0,0,480,480,pixels)!=ESP_OK)return false;
    ++frames;return true;
  }
  bool touch(bool& pressed,unsigned& x,unsigned& y) {
    pressed=false;completedTap=false;if(!touchReady)return false;
    uint32_t events=touchIrqs;bool event=events!=seenIrqs;seenIrqs=events;
    Wire.beginTransmission(ADDR_TOUCH_CST820);Wire.write(0x01);
    if(Wire.endTransmission(false)!=0 || Wire.requestFrom(ADDR_TOUCH_CST820,uint8_t(6))!=6){++touchErrors;return false;}
    touchGesture=Wire.read();uint8_t p=Wire.read(),xh=Wire.read(),xl=Wire.read(),yh=Wire.read(),yl=Wire.read();touchPoints=p&15;++touchSamples;
    x=((xh&15)<<8)|xl;y=((yh&15)<<8)|yl;
    pressed=(p&15)==1 && x<480 && y<480;
    completedTap=event && touchGesture==5 && !pressed && x<480 && y<480;return true;
  }
};
