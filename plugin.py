# Basic Python Plugin Example
#
# Author: Jan-Jaap Kostelijk
#
"""
<plugin key="SolarForecast" name="Solar Forecast" author="Jan-Jaap Kostelijk" version="0.1.3" externallink="https://github.com/JanJaapKo/SolarForecast">
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
        <param field="Mode6" label="Refresh interval" width="75px">
            <description>Please note that free option only supports 12 updates per hour (5minutes)</description>
            <options>
                <option label="5m" value="30"/>
                <option label="10m" value="60" default="true"/>
                <option label="15m" value="90"/>
                <option label="1hr" value="360"/>
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
    runCounter = 0
    location = dict()
    doneForToday = False
    debug = False

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
        self.runCounter = int(Parameters['Mode6'])
        self.location["latitude"], self.location["longitude"] = Settings["Location"].split(";")
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
        self.runCounter = self.runCounter - 1
        if self.runCounter <= 0:
            # Domoticz.Debug("Poll unit")
            self.runCounter = int(Parameters['Mode6'])
            #if (not self.doneForToday and datetime.now().hour >= 22) or self.debug:
            if (datetime.now().hour >= 22) or self.debug:
                data = self.getData(self.location["latitude"], self.location["longitude"], self.dec, self.az, self.kwp)
                # only update once per day after 22:00
                Domoticz.Debug("time to update devices!!!!")
                self.queryFromTo(self.deviceId, 1)
                if data:
                    self.updateDevices(data)
                    self.doneForToday = True

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
