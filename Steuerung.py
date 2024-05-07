#!/usr/bin/python
# -*- coding: utf-8 -*-

# 150/1000000 möglich
# 10-000802395a3e innen
# 10-000802394c3f Nachlauf
# 28-00000a47b3db Vorlauf
# neuer Sensor für Vorlauf
# 28-00000c34e7e1 Vorlauf
import logging
import logging.handlers as handlers
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP
import RPi.GPIO as GPIO
import time
import paho.mqtt.client as mqtt
import helper

config = helper.read_config()

########logging##########
logger=logging.getLogger()
logger.setLevel(logging.INFO)

filehandler=handlers.RotatingFileHandler(
    "HZlogs.txt", maxBytes=20000, backupCount=3)
logger.addHandler(filehandler)
filehandler.setLevel(logging.DEBUG)

streamhandler=logging.StreamHandler()
logger.addHandler(streamhandler)
streamhandler.setLevel(logging.DEBUG)

formater = logging.Formatter("%(asctime)s, %(levelname)s, %(message)s")
filehandler.setFormatter(formater)
streamhandler.setFormatter(formater)

##########ende Logging##############

MQTT_USERNAME = config['MqttSettings']['mqtt_username']
MQTT_PASSWORT = config['MqttSettings']['mqtt_passwort']
MQTT_HOST = config['MqttSettings']['mqtt_host']
MQTT_PORT = int(config['MqttSettings']['mqtt_port'])
mqtt_topic_status = "Smarthome/HWR1/Heizung/Status"
mqtt_ltw = "und wech"

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
BEREICH = 196000
intStellung = 0
sollstatus=""

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
       '28-00000c34e7e1':'Vorlauf'}

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
        #und dann?

def on_message(client, userdata, msg):
    global sollstatus
    strmsg = str(msg.payload.decode("utf-8"))
    logger.debug("Nachricht: " + strmsg)
    logger.debug("Topic: " + msg.topic)
    if msg.topic == "Smarthome/HWR1/Heizung/Heizstatus":
        if strmsg== "on":
            sollstatus="on"
            betrieb()
        elif strmsg == "off":
            sollstatus="off"
            schliessen()
        else:
            logger.error("unknow keyword: " + strmsg)
    elif msg.topic == "Smarthome/HWR1/Heizung/SMStellung" and sollstatus == "on":
        logger.info("Schrittmotor auf Position " + strmsg + " stellen")
        zustellen(int(strmsg))

def on_disconnect(client, userdata, rc):
    logger.error("disconnectiong reason " + str(rc))
    #und nun? Verbindung zum mqtt-broker verloren?
    schliessen()

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
    time.sleep(0.5)
    stepps("close",BEREICH)
    #Schrittmotortreiber schlafen legen
    GPIO.output(pin_sleep, False)
    time.sleep(0.2) #kurz mal warten

def betrieb():
    GPIO.output(pin_sleep, True)
    zustellen(8000) #Auf Position 8000 fahren
    #Pumpe anschalten
    GPIO.output(pin_pump, True)
    logger.info("Anlage im Betrieb")    

def zustellen(pos):
    global intStellung
    logger.debug("aktuelle Wert in Stellung: " + str(intStellung))
    if pos > intStellung:
        stepps("open",pos-intStellung)
        intStellung=pos
    elif pos < intStellung:
        stepps("close",intStellung-pos)
        intStellung=pos
    logger.info("Position " + str(intStellung) + " erreicht")
    client.publish("Smarthome/HWR1/Heizung/istPosition", str(intStellung), retain= True)

def schliessen():
    #Ventil auf 0 fahren
    zustellen(0)
    #Pumpe abschalten    
    GPIO.output(pin_pump, False)
    #Motortreiber abschalten
    GPIO.output(pin_sleep,False)
    logger.info("Anlage abgeschaltet/Standby")

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORT)
client.will_set(mqtt_topic_status, payload="und wech", qos=0, retain=True)
client.connect(MQTT_HOST, MQTT_PORT, 60)

logger.info("Referenz-Fahrt starten")
Reffahrt()
logger.info("mqtt starten")
client.loop_start()
client.publish("Smarthome/HWR1/Heizung/Status", "online", retain= True)
try:
    while True:
        for sensor in sensors: #Sensorwerte übertragen 
            global device_file
            device_file = base_dir + str(sensor) + '/w1_slave'
            #logger.info(sensors[sensor])#Sensorname
            temp = read_temp()
            #logger.info(temp)  #Sensorwert
            client.publish("Smarthome/HWR1/Heizung/Temp/" + sensors[sensor], str(temp))

        time.sleep(10)

except KeyboardInterrupt:
    logger.info("Programm abgebrochen")

#wenn Abbruch    
schliessen()
client.publish("Smarthome/HWR1/Heizung/SMStellung", "0", retain = True) #Sollpostion auf 0 stellen
client.publish("Smarthome/HWR1/Heizung/Status", "offline", retain =True)
client.disconnect()
client.loop_stop()
GPIO.cleanup()
logger.info("Programm beendet, System heruntergefahren")