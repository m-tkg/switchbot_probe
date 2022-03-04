#!/usr/bin/env python3

# -*- coding: utf-8 -*-
from bluepy.btle import Scanner, DefaultDelegate
from datetime import datetime
import time
import json
import os
from socket import gethostname
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway


class ScanDelegate(DefaultDelegate):
    def __init__(self):
        self.device_list = {}
        self.device_time_list = {}
        DefaultDelegate.__init__(self)
        with open(os.path.dirname(os.path.abspath(__file__)) + '/settings.json', 'r') as f:
            settings = json.loads(f.read())
            self.device_names = settings["devices"]
            self.pushgateway = settings["pushgateway"]


    def handleDiscovery(self, dev, isNewDev, isNewData):
        mac = 0
        temperature = None
        humidity = None
        position = None
        value_16b = ''

        advertise = dev.getScanData()
        for (adtype, desc, value) in advertise:
            if desc == '16b Service Data':
                value_16b = value
                model = value[4:6]
                mode  = value[6:8]
                battery = 0
                mac = dev.addr
                if model == '54': # switchbot meter
                    tempFra = int(value[11:12].encode('utf-8'), 16) / 10.0
                    tempInt = int(value[12:14].encode('utf-8'), 16)
                    if tempInt < 128:
                        tempInt *= -1
                        tempFra *= -1
                    else:
                        tempInt -= 128
                    temperature = tempInt + tempFra
                    humidity = int(value[14:16].encode('utf-8'), 16) % 128
                    battery = int(value[8:10], 16) & 0x7F

                elif model == '63': # switchbot curtain
                    battery = int(value[8:10], 16) & 0x7F
                    position = int(value[10:12], 16) & 0x7F

                elif model == '62': # switchbot button
                    battery = int(value[8:10], 16) & 0x7F

                elif model == '6d': # switchbot hub mini
                    battery = None

                elif model == '64': # switchbot contact
                    battery = None
            elif desc == 'Complete 128b Services' and value == 'cba20d00-224d-11e6-9fb8-0002a5d5c51b':
                    mac = dev.addr
        if mac != 0 :
            device = self.device_names.get(mac.upper(), None)
            if device is None:
                print(f"Unknown device: {mac}, value: {value_16b}")
            else:
                data = {}
                data["location"] = device["location"]
                data["type"] = device["type"]
                data["name"] = device["name"]
                data["battery"] = battery
                data["temperature"] = temperature
                data["humidity"] = humidity
                data["position"] = position
                self.device_list[mac] = data
                self.device_time_list[mac] = datetime.now()
                print(str(datetime.now()), len(self.device_list), data, value_16b)
                registry = CollectorRegistry()
                metrics = "switchbot_probe_uptime {counter}\n".format(counter=int(time.time()))
                Gauge(
                    "switchbotprobe_uptime",
                    "Uptime of switchbot_probe",
                    registry=registry,
                ).set(int(time.time()))
                battery = Gauge(
                    "switchbot_battery",
                    "Battery of switchbot",
                    ["type", "location", "name"],
                    registry=registry,
                )
                temperature = Gauge(
                    "switchbot_temperature",
                    "Temperatur of each room.",
                    ["type", "location", "name"],
                    registry=registry,
                )
                humidity = Gauge(
                    "switchbot_humidity",
                    "Humidity of each room.",
                    ["type", "location", "name"],
                    registry=registry,
                )
                position = Gauge(
                    "switchbot_curtain_position",
                    "Humidity of each room.",
                    ["type", "location", "name"],
                    registry=registry,
                )
                jobname = "switchbot_" + gethostname()
                for k, v in self.device_list.items():
                    if v["battery"] is not None:
                        battery.labels(type=v["type"], location=v["location"], name=v["name"]).set(v["battery"])
                    if v["temperature"] is not None:
                        temperature.labels(type=v["type"], location=v["location"], name=v["name"]).set(v["temperature"])
                    if v["humidity"] is not None:
                        humidity.labels(type=v["type"], location=v["location"], name=v["name"]).set(v["humidity"])
                    if v["position"] is not None:
                        position.labels(type=v["type"], location=v["location"], name=v["name"]).set(v["position"])
                try:
                    push_to_gateway(self.pushgateway, job=jobname, registry=registry)
                except:
                    print(str(datetime.now()), "error push metrics")

                return


start_time = datetime.now()
Scanner().withDelegate(ScanDelegate()).scan(0.0)
