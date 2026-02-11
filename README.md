# SolarForecast
Domoticz plugin to fetch solar power forecast data from the [Nationaal Energie Dashboard (NED)](https://ned.nl/nl/zonne-energievoorspeller) API<br><br>

Fetches hourly solar power forecasts for Dutch provinces from the official NED API<br><br>
Remark: The forecast data is regional/provincial aggregate data, not specific to individual installations<br>

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
git clone https://github.com/JanJaapKo/NEDsolarForecast
```
to update:
```
cd domoticz/plugins/SolarForecast
git pull https://github.com/JanJaapKo/NEDsolarForecast
```
2. Restart domoticz
3. Go to step configuration


## Configuration
Fill in the following parameters (mandatory unless marked optional):
- Panels declination in degrees: how 'steep' the panels are mounted on the roof:  0 (horizontal) … 90 (vertical)
- Panels azimuth in degrees: Angle of the solar panels to earth compass: -180 … 180 (-180 = north, -90 = east, 0 = south, 90 = west, 180 = north)
- Panels peak power in kiloWatt: the peak power of the installation (for reference only; data comes from NED API)
- API key (mandatory): Your personal NED API key - obtain from https://ned.nl/user by creating an account
- Location: Select your location in the Netherlands for forecast data:
  - Nederland (national forecast)
  - Groningen
  - Friesland
  - Drenthe
  - Overijssel
  - Flevoland
  - Gelderland
  - Utrecht
  - Noord-Holland
  - Zuid-Holland
  - Zeeland
  - Noord-Brabant
  - Limburg
- Debug: Set debug logging level (Verbose/Debug/Normal)

