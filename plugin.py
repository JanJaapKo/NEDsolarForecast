# Basic Python Plugin Example
#
# Author: Jan-Jaap Kostelijk
#
"""
<plugin key="NEDsolarForecast" name="NED solar forecast" author="Jan-Jaap Kostelijk" version="0.0.3" externallink="https://github.com/JanJaapKo/NEDsolarForecast">
    <description>
        Solar power forecast plugin<br/><br/>
        Fetches solar power forecast from the site solar.forecast<br/><br/><br/>
    </description>
    <params>
		<param field="Mode1" label="Panels declination" width="30px" required="true" default="45">
            <description>Angle of the solar panels to earth surface: 0 (horizontal) … 90 (vertical)</description>
        </param>
		<param field="Mode2" label="Panels azimuth" width="30px" required="true" default="0">
            <description>Angle of the solar panels to earth compass: -180 … 180 (-180 = north, -90 = east, 0 = south, 90 = west, 180 = north)</description>
        </param>
		<param field="Mode3" label="Panels peak power" width="30px" required="true" default="4.8">
            <description>Installed power of the modules in kilo Watt [kW]</description>
        </param>
		<param field="Mode5" label="API key" width="200px" required="true">
            <description>Your personal NED API key - obtain from https://ned.nl/user</description>
        </param>
		<param field="Mode4" label="Debug" width="75px">
            <options>
                <option label="Verbose" value="Verbose"/>
                <option label="True" value="Debug" default="true"/>
                <option label="False" value="Normal"/>
            </options>
        </param>
        <param field="Mode6" label="Location" width="100px">
            <description>Select your location in the Netherlands</description>
            <options>
                <option label="Nederland" value="0" default="true"/>
                <option label="Groningen" value="1"/>
                <option label="Friesland" value="2"/>
                <option label="Drenthe" value="3"/>
                <option label="Overijssel" value="4"/>
                <option label="Flevoland" value="5"/>
                <option label="Gelderland" value="6"/>
                <option label="Utrecht" value="7"/>
                <option label="Noord-Holland" value="8"/>
                <option label="Zuid-Holland" value="9"/>
                <option label="Zeeland" value="10"/>
                <option label="Noord-Brabant" value="11"/>
                <option label="Limburg" value="12"/>
            </options>
        </param>
    </params>
</plugin>
"""
try:
	import DomoticzEx as Domoticz
	debug = False
except ImportError:
    from fakeDomoticz import *
    from fakeDomoticz import Domoticz
    Domoticz = Domoticz()
    debug = True

import json
import time
import requests
import math
from datetime import datetime, timedelta, date

class SolarForecastPlug:
    #define class variables
    location_code = '0'
    doneForToday = False
    debug = False
    APIkey = ""
    last_api_call = None
    
    # Location names for Netherlands provinces
    locations = {
        '0': {'name': 'Nederland', 'latitude': 52.13, 'longitude': 5.29},
        '1': {'name': 'Groningen', 'latitude': 53.22, 'longitude': 6.57},
        '2': {'name': 'Friesland', 'latitude': 53.14, 'longitude': 5.79},
        '3': {'name': 'Drenthe', 'latitude': 52.96, 'longitude': 6.39},
        '4': {'name': 'Overijssel', 'latitude': 52.50, 'longitude': 6.27},
        '5': {'name': 'Flevoland', 'latitude': 52.67, 'longitude': 5.52},
        '6': {'name': 'Gelderland', 'latitude': 52.04, 'longitude': 5.87},
        '7': {'name': 'Utrecht', 'latitude': 52.09, 'longitude': 5.12},
        '8': {'name': 'Noord-Holland', 'latitude': 52.50, 'longitude': 4.79},
        '9': {'name': 'Zuid-Holland', 'latitude': 51.97, 'longitude': 4.48},
        '10': {'name': 'Zeeland', 'latitude': 51.50, 'longitude': 3.60},
        '11': {'name': 'Noord-Brabant', 'latitude': 51.50, 'longitude': 5.04},
        '12': {'name': 'Limburg', 'latitude': 50.87, 'longitude': 5.71}
    }

    def __init__(self):
        pass

    def onStart(self):
        Domoticz.Log("onStart called")
        if Parameters['Mode4'] == 'Debug' or self.debug == True:
            Domoticz.Debugging(2)
            DumpConfigToLog()
            self.debug = True
        if Parameters['Mode4'] == 'Verbose':
            Domoticz.Debugging(1)
            DumpConfigToLog()

        #read out parameters
        self.location_code = Parameters['Mode6']
        Domoticz.Debug(f"Using location: {self.locations[self.location_code]['name']} (code: {self.location_code})")
        self.dec = int(Parameters['Mode1'])
        self.az = int(Parameters['Mode2'])
        self.kwp = float(Parameters['Mode3'])
        self.APIkey = Parameters['Mode5']
        if len(self.APIkey) == 0:
            Domoticz.Error("API key is required to use the NED API")

        self.deviceId = "SolarForecast"
        self.deviceId = Parameters['Name']
        Domoticz.Device(DeviceID=self.deviceId) 
        if self.deviceId not in Devices or (1 not in Devices[self.deviceId].Units):
            #Options={"AddDBLogEntry" : "true", "DisableLogAutoUpdate" : "true"}
            #Options={"AddDBLogEntry" : "true"}
            #Domoticz.Unit(Name=self.deviceId + ' - 24h forecast', Unit=1, Type=243, Subtype=33, Switchtype=4,  Used=1, Options=Options, DeviceID=self.deviceId).Create()
            Domoticz.Unit(Name=self.deviceId + ' - 24h forecast', Unit=1, Type=243, Subtype=33, Switchtype=4,  Used=1, DeviceID=self.deviceId).Create()
            
        data = self.getData(self.location_code)
        if data:
            self.updateDevices(data)
        self.doneForToday = False

    def onStop(self):
        Domoticz.Debug("onStop called")

    def onCommand(self, DeviceId, Unit, Command, Level, Hue):
        Domoticz.Debug("onCommand: DeviceId: '"+str(DeviceId)+"' Unit: '"+str(Unit)+"', Command: '"+str(Command)+"', Level: '"+str(Level)+"', Hue: '"+str(Hue)+"'")

    def onHeartbeat(self):
        #Domoticz.Debug("onHeartbeat called")
        current_hour = datetime.now().hour
        current_time = datetime.now()
        should_poll = False
        
        # Check if we should poll the API
        if (current_hour == 22 or current_hour == 23):
            # Normal polling hours: once per day
            if not self.doneForToday:
                should_poll = True
                self.doneForToday = True
        elif self.debug:
            # Debug mode: maximum once per minute
            if self.last_api_call is None or (current_time - self.last_api_call).total_seconds() >= 60:
                should_poll = True
                self.last_api_call = current_time
        
        # Reset the flag when we're outside the polling hours
        if current_hour == 21:
            self.doneForToday = False
        
        # Execute the poll if conditions are met
        if should_poll:
            data = self.getData(self.location_code)
            Domoticz.Debug("time to update devices!!!!")
            self.queryFromTo(self.deviceId, 1)
            if data:
                self.updateDevices(data)

    def getData(self, location_code):
        """Fetch solar forecast data from NED API"""
        baseUrl = "https://api.ned.nl/v1/utilizations"
        
        headers = {
            'X-AUTH-TOKEN': self.APIkey,
            'accept': 'application/json'
        }
        
        # Calculate date range: today and tomorrow
        today = date.today()
        tomorrow = today + timedelta(days=1)
        day_after = tomorrow + timedelta(days=1)
        
        params = {
            'point': location_code,
            'type': 2,  # Solar
            'granularity': 5,  # Hour granularity
            'granularitytimezone': 1,  # CET (Central European Time)
            'classification': 1,  # Forecast
            'activity': 1,  # Providing (production)
            'validfrom[after]': str(today),
            'validfrom[strictly_before]': str(day_after)
        }
        
        try:
            response = requests.get(baseUrl, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            Domoticz.Debug(f"API call successful. URL: {response.url}")
            return data
        except requests.exceptions.RequestException as e:
            Domoticz.Error(f"Error calling NED API: {str(e)}")
            return False

    def calculate_solar_correction(self, hour, capacity, location_code):
        """
        Calculate solar position correction based on panel orientation and sun position.
        Converts API capacity to actual expected energy based on solar geometry.
        """
        try:
            # Get location coordinates
            location = self.locations[location_code]
            latitude = location['latitude']
            longitude = location['longitude']
            
            # Solar position calculations
            current_date = datetime.now()
            day_of_year = current_date.timetuple().tm_yday
            
            # Calculate solar declination (angle of sun relative to equator)
            angular_speed = 360 / 365.25
            declination_rad = math.asin(0.3978 * math.sin(math.radians(angular_speed * 
                            (day_of_year - (81 - 2 * math.sin(math.radians(angular_speed * (day_of_year - 2))))))))
            declination = math.degrees(declination_rad)
            
            # Convert parameters to radians
            lat_rad = math.radians(latitude)
            lon_rad = math.radians(longitude)
            decl_rad = math.radians(declination)
            
            # Time calculations
            solar_hour = hour + (4 * longitude / 60)
            hourly_angle = 15 * (12 - solar_hour)
            hourly_angle_rad = math.radians(hourly_angle)
            
            # Calculate sun altitude and azimuth
            sin_altitude = (math.sin(lat_rad) * math.sin(decl_rad) + 
                           math.cos(lat_rad) * math.cos(decl_rad) * math.cos(hourly_angle_rad))
            sin_altitude = max(-1, min(1, sin_altitude))  # Clamp to valid range
            sun_altitude = math.degrees(math.asin(sin_altitude))
            
            # Sun azimuth calculation
            cos_azimuth = ((math.sin(decl_rad) - math.sin(lat_rad) * math.sin(math.radians(sun_altitude))) / 
                          (math.cos(lat_rad) * math.cos(math.radians(sun_altitude))))
            cos_azimuth = max(-1, min(1, cos_azimuth))  # Clamp to valid range
            sun_azimuth = math.degrees(math.acos(cos_azimuth))
            
            # Determine azimuth sign
            sin_azimuth = (math.cos(decl_rad) * math.sin(hourly_angle_rad)) / math.cos(math.radians(sun_altitude))
            if sin_azimuth < 0:
                sun_azimuth = 360 - sun_azimuth
            
            # Calculate directional correction factors
            correction = 0.0
            
            if capacity > 0 and sun_altitude > -2:
                # Azimuth difference between sun and panel
                az_diff = sun_azimuth - self.az
                if az_diff > 180:
                    az_diff = az_diff - 360
                elif az_diff < -180:
                    az_diff = az_diff + 360
                
                # Direct radiation factor based on azimuth
                if az_diff >= -55:
                    direct_factor = 1.0
                elif az_diff >= -100:
                    direct_factor = max(0.15, (az_diff + 100) / 45)
                else:
                    direct_factor = 0.1
                
                # Altitude factor (accounts for low sun angles)
                if sun_altitude <= -2:
                    alt_factor = 0
                elif sun_altitude < 5:
                    alt_factor = 0.15 + 0.85 * (sun_altitude + 2) / 7
                else:
                    alt_factor = 1.0
                
                direct_factor = direct_factor * alt_factor
                diffuse_factor = 0.18 * alt_factor
                correction = min(1.0, direct_factor + diffuse_factor)
            
            # Calculate final energy in kWh
            kwh = self.kwp * (capacity / 100.0) * correction
            
            Domoticz.Debug(f"Hour {hour}: capacity={capacity:.2f}%, sunAz={sun_azimuth:.1f}°, sunAlt={sun_altitude:.1f}°, correction={correction:.3f}, kWh={kwh:.3f}")
            
            return kwh
            
        except Exception as e:
            Domoticz.Error(f"Error calculating solar correction: {str(e)}")
            return 0.0

    def updateDevices(self, data):
        """Update devices with solar forecast data from NED API"""
        try:
            Domoticz.Debug(f"Processing {len(data)} data points from NED API")
            
            # Track daily and hourly totals
            daily_totals = {}
            
            if not isinstance(data, list):
                Domoticz.Error("Unexpected data format from NED API")
                return
            
            # Process each utilization record
            for utilization in data:
                try:
                    validfrom = utilization.get('validfrom', '')
                    capacity = utilization.get('capacity', 0)  # in percentage (0-100)
                    
                    if not validfrom:
                        continue
                    
                    dateline = datetime.fromisoformat(validfrom)
                    hour = dateline.hour
                    
                    # Apply solar position correction
                    corrected_kwh = self.calculate_solar_correction(hour, capacity, self.location_code)
                    
                    # Calculate watts for display
                    watts = int(corrected_kwh * 1000)  # Convert kWh to W
                    
                    # Build sValue: watts;wh;timestamp
                    sValue = f"{watts};{corrected_kwh:.3f};{validfrom}"
                    
                    Domoticz.Debug(f"Updating device with: capacity={capacity}%, corrected_kwh={corrected_kwh:.3f}kWh, time={validfrom}")
                    self.UpdateDevice(self.deviceId, 1, 0, sValue)
                    
                    # Track daily total
                    day_key = dateline.date()
                    if day_key not in daily_totals:
                        daily_totals[day_key] = 0
                    daily_totals[day_key] += corrected_kwh
                    
                except (KeyError, ValueError, TypeError) as e:
                    Domoticz.Debug(f"Error processing utilization record: {str(e)}")
                    continue
            
            Domoticz.Debug("successful data received and processed")
            
        except Exception as e:
            Domoticz.Error(f"Error updating devices: {str(e)}")
        
    def queryFromTo(self, Device, Unit):
        # see for which dates a device holds data
        Domoticz.Debug("the IDX should be "+ str(Devices[Device].Units[Unit].ID) + " for device " + str(Devices[Device].Units[Unit].Name))

    def UpdateDevice(self, Device, Unit, nValue, sValue, AlwaysUpdate=False, Name=""):
        # Make sure that the Domoticz device still exists (they can be deleted) before updating it
        if (Device in Devices and Unit in Devices[Device].Units):
            if (Devices[Device].Units[Unit].nValue != nValue) or (Devices[Device].Units[Unit].sValue != sValue) or AlwaysUpdate:
                    Domoticz.Debug("Updating device '"+Devices[Device].Units[Unit].Name+ "' with current sValue '"+Devices[Device].Units[Unit].sValue+"' to '" +sValue+"'")
                    if isinstance(nValue, int):
                        Devices[Device].Units[Unit].nValue = nValue
                    else:
                        Domoticz.Log("nValue supplied is not an integer. Device: "+str(Device)+ " unit "+str(Unit)+" nValue "+str(nValue))
                        Devices[Device].Units[Unit].nValue = int(nValue)
                    Devices[Device].Units[Unit].sValue = sValue
                    if Name != "":
                        Devices[Device].Units[Unit].Name = Name
                    Devices[Device].Units[Unit].Update()
                    
        else:
            Domoticz.Error("trying to update a non-existent unit "+str(Unit)+" from device "+str(Device))
        return
        
global _plugin
_plugin = SolarForecastPlug()

def onStart():
    global _plugin
    _plugin.onStart()

def onStop():
    global _plugin
    _plugin.onStop()

def onCommand(DeviceId, Unit, Command, Level, Color):
    global _plugin
    _plugin.onCommand(DeviceId, Unit, Command, Level, Color)

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()

    # Generic helper functions
def DumpConfigToLog():
    Domoticz.Debug("Parameter count: " + str(len(Parameters)))
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug( "Parameter '" + x + "':'" + str(Parameters[x]) + "'")
    for x in Settings:
        if Settings[x] != "":
            Domoticz.Debug( "Setting '" + x + "':'" + str(Settings[x]) + "'")
    # Configurations = getConfigItem()
    # Domoticz.Debug("Configuration count: " + str(len(Configurations)))
    # for x in Configurations:
        # if Configurations[x] != "":
            # Domoticz.Debug( "Configuration '" + x + "':'" + str(Configurations[x]) + "'")
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug("Device:           " + str(x) + " - " + str(Devices[x]))
    return
