# ant_bms
Ant BMS Python logger to influxdb

The Python script reads the ANT BMS via Bluetooth and transfers the data to the InfluxDB database.

This is a working but not yet finished version.

I still have a few problems with the bluetooth module of the Rasperry Pi 4.
On the one hand, the Bluetooth is not always switched off properly when you restart. Therefore I have the script rc6.d_K99_bluetooth_power_off running in rc6.d.

When the Rasperry Pi 4 is raised, there are occasional problems that the Bluetooth does not establish a connection.
That's what the script ant_bms.sh is for
This is started via crontab with @reboot and then executes the get_ant-BMS.py Python script in a loop.

The get_ant-BMS.py outputs some data as debug info in the console, and also logs this into the InfluxdB. 


######
everyone who wants to play around with it is very welcome.
When I find the time again, I will also make the temporary solution better. 


Example Output
```python
{'BMS Balance Temperature': 33,
 'BMS Cell Sensor 1 Temperature': 32,
 'BMS Cell Sensor 2 Temperature': 31,
 'BMS Current': 0.0,
 'BMS Temperature': 32,
 'BMS Voltage': 52.9,
 'Balancing Status': 'OFF',
 'Battery Remaining Ah': 277.518761,
 'Battery physical Ah': 0.0,
 'Cell Avg Voltage': 3.304,
 'Cell Diff Voltage': 0.009000000000000341,
 'Cell Max Voltage': 3.309,
 'Cell Min Voltage': 3.3,
 'Charge MOSFET Status': 'ON',
 'Discharge MOSFET Status': 'ON',
 'Power Watt': 0.0,
 'State of Carge': 100,
 'Total battery cycle Ah': 0.0}
```
