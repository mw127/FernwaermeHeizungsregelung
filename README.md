# Fernwärme Heizungsregelung
Ein Projekt welches die Wärmeentnahme einer Fernwärme-Übergabestation regelt. Dies betrifft nur den Heizungskreislauf und nicht die Aufbereitung des Brauchwarmwassers.

---
Die Einspeisung der Fernwärme in das eigene Heizungssystem, wird über Ventil geregelt, welches eines Eckventils eines Heizkörpers ähnelt.
Es soll nur soviel heißes Wasser eingespeist werden wie nötig, daher muss das Ventil gesteuert werden.

Die Höhe des Ventilstiftes und damit die Durchflussmenge, wird über eine Gewindewelle eingestellt. Die Welle besitzt ein Zahnrad und dieses wird über ein weiteres Zahnrad angetrieben, welches über den Schrittmotor gesteuert wird.

An der Aufnahme des Schrittmotors ist ein Endschalter montiert, welcher angefahren werden muss, um einen definierten Zustand zu erreichen.
Zwischen Endschalter und Ventil geschlossen wurden 196000 Schritte des Schrittmotors ermitteln. Dabei handelt es sich um Microschritte (1/32 Stepps).

Um die Vorlauf/Nachlauftemperatur zu regeln, sind an den entsprechenden Rohren, Temperatursensoren montiert.

Sensorwerte, Schrittmotorstellung, Systemzustand werden per mqtt mitgeteilt.



Verbaute Hardware:
- Raspberry Pi 3b
- Pololu DRV8825 Stepper Motor Driver
- Schrittmotor NEMA 
- Verbindungs Aufnahme für Schrittmotor und Getrieb
