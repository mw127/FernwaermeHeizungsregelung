# Eine kleine Routine um die Ansteuerung der Umwälzpumpe zu testen
from gpiozero import Button, DigitalOutputDevice


PIN_PUMP = 27
pump = DigitalOutputDevice(PIN_PUMP)

try:
    while True:
        strinput = input("Pumpe on/off: ")
        if strinput == "on":
            pump.on()
        elif strinput == "off":
            pump.off()
        else:
            break

except KeyboardInterrupt:
    print("ende")
pump.off()