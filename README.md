# SolarForecast
Domoticz plugin to fetch [Solar Forecast](https://forecast.solar/) data<br><br>

Preliminary version, breaking changes to be expected!<br>
reads forecasted solar power prediction for a given solar panel installation<br><br>
Remark: if you have sets of panels in (very) different orientations, make a Hardware entry for each and make a Domoticz script to add them together<br>

## Prerequisites

- Follow the Domoticz guide on [Using Python Plugins](https://www.domoticz.com/wiki/Using_Python_plugins) to enable the plugin framework.

The following Python modules installed
```
sudo apt-get update
sudo apt-get install python3-requests
```

## Installation

1. Clone repository into your domoticz plugins folder
```
cd domoticz/plugins
git clone https://github.com/JanJaapKo/SolarForecast
```
to update:
```
cd domoticz/plugins/SolarForecast
git pull https://github.com/JanJaapKo/SolarForecast
```
2. Restart domoticz
3. Go to step configuration


## Configuration
Fill in the following parameters (mandatory unless marked optional):
- Panels declination in degrees: how 'steep' the panels are mounted on the roof:  0 (horizontal) … 90 (vertical)
- Panels azimuth in degrees: Angle of the solar panels to earth compass: -180 … 180 (-180 = north, -90 = east, 0 = south, 90 = west, 180 = north)
- Panels peak power in kiloWatt: the peak power of the installation
- Optional: enter your API key to allow more frequent and more detailed forecasts
