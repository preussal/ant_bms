#/bin/bash

/usr/bin/rfcomm release hci0

# Da das Bluetooth Spinnt muss ich hier ca 2 Min warten
sleep 150
service hciuart restart

#service bluetooth restart
#bluetoothctl power off; sleep 1; bluetoothctl power on
#rfkill unblock all

# Bluetooth MAC Adresse der ANT BMS
# rfcomm verbindung herstellen.
/usr/bin/rfcomm bind hci0 AA:BB:CC:A1:23:45 >/dev/null 2>&1

while true; do
	/usr/bin/python /opt/ant_bms/get_ant-BMS.py >/dev/null 2>&1
done
