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
		<param field="Mode5" label="API key" width="200px" required="false">
            <description>Optional: provide your personal API key</description>
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
from datetime import datetime, timedelta, date

class SolarForecastPlug:
    #define class variables
    location = dict()
    doneForToday = False
    debug = False
    
    # Location coordinates for Netherlands provinces
    locations = {
        '0': {'name': 'Nederland', 'lat': None, 'lon': None},  # Uses Settings["Location"]
        '1': {'name': 'Groningen', 'lat': '53.2', 'lon': '6.6'},
        '2': {'name': 'Friesland', 'lat': '53.0', 'lon': '5.8'},
        '3': {'name': 'Drenthe', 'lat': '53.0', 'lon': '6.6'},
        '4': {'name': 'Overijssel', 'lat': '52.5', 'lon': '6.8'},
        '5': {'name': 'Flevoland', 'lat': '52.6', 'lon': '5.3'},
        '6': {'name': 'Gelderland', 'lat': '52.0', 'lon': '6.0'},
        '7': {'name': 'Utrecht', 'lat': '52.1', 'lon': '5.2'},
        '8': {'name': 'Noord-Holland', 'lat': '52.5', 'lon': '5.1'},
        '9': {'name': 'Zuid-Holland', 'lat': '51.9', 'lon': '4.5'},
        '10': {'name': 'Zeeland', 'lat': '51.4', 'lon': '3.9'},
        '11': {'name': 'Noord-Brabant', 'lat': '51.5', 'lon': '5.0'},
        '12': {'name': 'Limburg', 'lat': '51.2', 'lon': '5.7'}
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
        location_code = Parameters['Mode6']
        if location_code == '0':
            # Use Domoticz location setting
            self.location["latitude"], self.location["longitude"] = Settings["Location"].split(";")
        else:
            # Use predefined province location
            self.location["latitude"] = self.locations[location_code]['lat']
            self.location["longitude"] = self.locations[location_code]['lon']
        Domoticz.Debug(f"Using location: {self.locations[location_code]['name']}")
        Domoticz.Debug("self.location.latitude, self.location.longitude = " + str(self.location["latitude"]) +" "+ str(self.location["longitude"]))
        self.dec = int(Parameters['Mode1'])
        self.az = int(Parameters['Mode2'])
        self.kwp = float(Parameters['Mode3'])
        self.APIkey = ""
        if len(Parameters['Mode5']) > 0:
            self.APIkey = Parameters['Mode5'] + '/'

        self.deviceId = "SolarForecast"
        self.deviceId = Parameters['Name']
        Domoticz.Device(DeviceID=self.deviceId) 
        if self.deviceId not in Devices or (1 not in Devices[self.deviceId].Units):
            #Options={"AddDBLogEntry" : "true", "DisableLogAutoUpdate" : "true"}
            #Options={"AddDBLogEntry" : "true"}
            #Domoticz.Unit(Name=self.deviceId + ' - 24h forecast', Unit=1, Type=243, Subtype=33, Switchtype=4,  Used=1, Options=Options, DeviceID=self.deviceId).Create()
            Domoticz.Unit(Name=self.deviceId + ' - 24h forecast', Unit=1, Type=243, Subtype=33, Switchtype=4,  Used=1, DeviceID=self.deviceId).Create()
        # if self.deviceId not in Devices or (2 not in Devices[self.deviceId].Units):
            # Domoticz.Unit(Name=self.deviceId + ' - next hour', Unit=2, Type=243, Subtype=31, Options={'Custom': '1;Wh'},  Used=1, DeviceID=self.deviceId).Create()
            
        data = self.getData(self.location["latitude"], self.location["longitude"], self.dec, self.az, self.kwp)
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
        # Only poll API at 22:00 and 23:00 daily
        if (current_hour == 22 or current_hour == 23) or self.debug:
            if not self.doneForToday or self.debug:
                data = self.getData(self.location["latitude"], self.location["longitude"], self.dec, self.az, self.kwp)
                # only update once per day during these hours
                Domoticz.Debug("time to update devices!!!!")
                self.queryFromTo(self.deviceId, 1)
                if data:
                    self.updateDevices(data)
                    self.doneForToday = True
        else:
            # Reset the flag when we're outside the polling hours
            if current_hour == 21:
                self.doneForToday = False

    def getData(self, lat, lon, dec, az, kwp):
        baseUrl = "https://api.forecast.solar/" + self.APIkey + "estimate"
        response = requests.get(baseUrl +f"/{lat}/{lon}/{dec}/{az}/{kwp}")
        if len(response.json())>0:
            Domoticz.Debug("full url: "+str(response.url)+"; data message: "+str(response.json()["message"]["type"]) + " "+str(response.json()["message"]["text"]))
            # Domoticz.Debug("response headers: "+str(response.headers)+"; ")
        else:
            Domoticz.Error("empty reply from API")
            return False
        # Domoticz.Debug(json.dumps(response.json(),indent=4)) #only for manual testing
        return response.json()

    def updateDevices(self, json):
        message_type = json["message"]["type"]
        message_text = json["message"]["text"]
        if json["message"]["type"] != "success":
            #the response is not successful
            Domoticz.Error("Error requesting data: " + f"{message_type} : {message_text}")
        else:
            Domoticz.Debug("successful data received")
            for dtline in json["result"]["watt_hours_period"]:
                #only update for tomorrow
                #Domoticz.Debug("dtline = "+dtline)
                dateline = datetime.fromisoformat(dtline)
                if dateline.date() > date.today():
                    sValue = str(json["result"]["watts"][dtline])+";"+str(json["result"]["watt_hours_period"][dtline])+";"+str(dtline)
                    #sValue = "-1;"+str(json["result"]["watt_hours_period"][dtline])+";"+str(dtline)
                    #Domoticz.Debug("sValue = "+str(sValue))
                    self.UpdateDevice(self.deviceId, 1, 0, sValue)
            for dtline in json["result"]["watt_hours_day"]:
                dateline = datetime.fromisoformat(dtline)
                if dateline.date() > date.today():
                    sValue = "-1;"+str(json["result"]["watt_hours_day"][dtline])+";"+str(dtline)
                    Domoticz.Debug("sValue = "+str(sValue))
                    self.UpdateDevice(self.deviceId, 1, 0, sValue)
        
    def queryFromTo(self, Device, Unit):
        # see for which dataes a device holds data
        Domoticz.Debug("the IDX shoud be "+ str(Devices[Device].Units[Unit].ID) + " for device " + str(Devices[Device].Units[Unit].Name))

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
