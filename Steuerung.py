#!/usr/bin/python
# -*- coding: utf-8 -*-

# 150/1000000 möglich
# 10-000802395a3e innen
# 10-000802394c3f Nachlauf
# 28-00000a47b3db Vorlauf
import logging
import logging.handlers as handlers
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP
import RPi.GPIO as GPIO
import time
import paho.mqtt.client as mqtt

########logging##########
logger=logging.getLogger()
logger.setLevel(logging.DEBUG)

filehandler=handlers.RotatingFileHandler(
    "/home/mw/Pyton/HZlogs.txt", maxBytes=20000, backupCount=3)
filehandler.setLevel(logging.INFO)

streamhandler=logging.StreamHandler()
streamhandler.setLevel(logging.INFO)

formater = logging.Formatter("%(asctime)s, %(levelname)s, %(message)s")
filehandler.setFormatter(formater)
streamhandler.setFormatter(formater)

##########ende Logging##############

MQTT_USERNAME = "UserHz"
MQTT_PASSWORT = "YjByTM"
MQTT_HOST = "192.168.178.38"
MQTT_PORT = 1883
mqtt_topic_status = "Smarthome/HWR1/Heizung/Status"
mqtt_ltw = "und wech"

GPIO.setmode(GPIO.BCM)

BEREICH = 196000
intStellung = 0

# GPIO17 Endschalter
pin_endschalter = 17
GPIO.setup(pin_endschalter, GPIO.IN)
pin_dir = 20  # HIGH = open, LOW = Close
GPIO.setup(pin_dir, GPIO.OUT)
pin_step = 21
GPIO.setup(pin_step, GPIO.OUT)
pin_sleep = 16
GPIO.setup(pin_sleep, GPIO.OUT)
pin_pump =27
GPIO.setup(pin_pump, GPIO.OUT)

base_dir = '/sys/bus/w1/devices/'
sensors={'10-000802395a3e':"Innen",
       '10-000802394c3f':'Nachlauf',
       '28-00000a47b3db':'Vorlauf'}

# DIRECTION_PIN = 20
# STEP_PIN = 21
# ENABLE_MOTOR_PIN =
# END_POSITION_PIN = 17

def read_temp_raw():
    try:
        f = open(device_file,'r')
        lines = f.readlines()
        f.close
    except IOError as e:
        logger.error(e)
    return lines

def read_temp():
    lines = read_temp_raw()
    while lines[0].strip()[-3:] != 'YES':
        time.sleep(0.1)
        lines = read_temp_raw()
    equals_pos = lines[1].find('t=')
    if equals_pos != -1:
        temp_string = lines[1][equals_pos+2:]
        temp_c = float(temp_string)/1000.0
        temp_c = float(Decimal(str(temp_c)).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP))
        return temp_c

def on_connect(client, userdata, flags, rc):
    if rc==0:
        client.subscribe("Smarthome/HWR1/Heizung/#")
        client.publish(mqtt_topic_status, "online")
        logger.info("connected with mqtt-broker")
    else:
        logger.error("Bad connection Returned code=" + str(rc))

def on_message(client, userdata, msg):
    strmsg = str(msg.payload.decode("utf-8"))
    if msg.topic == "":
        if strmsg== "on":
            betrieb()
        elif strmsg == "off":
            schliessen()
        else:
            logger.error("unknow keyword: " + strmsg)
    elif msg.topic == "Smarthome/HWR1/Heizung/SMStellung":
        logger.info("Schrittmotor auf Position " + strmsg + " stellen")
        zustellen(int(strmsg))

def on_disconnect(client, userdata, rc):
    logger.error("disconnectiong reason " + str(rc))
    client.connected_flag = False


def onestep():
    GPIO.output(pin_step, True)
    time.sleep(150 / 1000000)
    GPIO.output(pin_step, False)
    time.sleep(150 / 1000000)

def stepps(dir, stepps):
    if dir == "open":
        GPIO.output(pin_dir, True)
    elif dir == "close":
        GPIO.output(pin_dir, False)

    for i in range(stepps):
        onestep()

def Reffahrt():
    # Treiber aufwecken
    GPIO.output(pin_sleep, True)
    while GPIO.input(pin_endschalter):
        stepps("open",1)
    #Endschalter erreicht
    #Ventil zufahren
    stepps("close",BEREICH)
    GPIO.output(pin_sleep, False)

def betrieb():
    GPIO.output(pin_sleep, True)
    zustellen(7000)
    #Auf Position 7000 fahren
    #Pumpe anschalten
    GPIO.output(pin_pump, True)    

def zustellen(pos):
    #auf Position 5000 fahren
    if pos > intStellung:
        stepps("open",pos-intStellung)
        intStellung=pos
    elif pos < intStellung:
        stepps("close",intStellung-pos)
        intStellung=pos
    print("dummy")

def schliessen():
    #Ventil auf 0 fahren
    zustellen(0)
    #Pumpe abschalten
    #Motortreiber abschalten
    GPIO.output(pin_pump, False)
    GPIO.output(pin_sleep,False)

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORT)
client.will_set(mqtt_topic_status, "und wech", 0, False)
client.connect(MQTT_HOST, MQTT_PORT, 60)

logger.info("Referenz-Fahrt starten")
Reffahrt()
logger.info("mqtt starten")
client.loop_start()

try:
    while True:
        for sensor in sensors: #Sensorwerte übertragen 
            global device_file
            device_file = base_dir + str(sensor) + '/w1_slave'
            logger.info(sensors[sensor])#Sensorname
            temp = read_temp()
            logger.info(temp)  #Sensorwert
            client.publish("Smarthome/HWR1/Heizung/Temp/" + sensors[sensor], str(temp))

        time.sleep(10)

except KeyboardInterrupt:
    logger.info("Programm abgebrochen")
    
schliessen()
GPIO.cleanup()
logger.info("Programm beendet")