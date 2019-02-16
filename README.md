# mikettle - Library for Xiaomi Mi Kettle with Bleutooth LE


This library properly authenticates with Xiaomi Mi Kettle and allows to read status and control the kettle via Bluetooth.

Based on https://github.com/ratcashdev/mitemp that is based on https://github.com/open-homeautomation/miflora .

This library uses authentication that was reverse engineered by aprosvetova (https://github.com/aprosvetova/xiaomi-kettle) and then customized and verified by me


I am still not sure about ProductId and how many different ProductIds there are. This needs to be investigated further.


## Functionality 
Supports reading of these values:
- Current action
- Current Mode
- Keep warm set temperature
- Current temperature
- Keep warm type
- Keep warm time

Supports controlling of these values:
- TBD

To use this library you will need a Bluetooth Low Energy dongle attached to your computer or Raspberry PI. You will also need a
Xiaomi Mi Kettle. 

To use with home-assistant please refer to documentation over at home assitant (TBD)

## Backend
Backend is using bluepy library. Please refer to installation instructions - https://github.com/IanHarvey/bluepy


## Conttributing
please have a look at [CONTRIBUTING.md](CONTRIBUTING.md)

----

## Projects Depending on `mikettle`

(TBD) https://github.com/home-assistant/home-assistant
