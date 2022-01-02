#!/usr/bin/env python

import sys
import time
import codecs
import bluetooth
import socket
import serial
import subprocess
from pathlib import Path
import struct
from binascii import unhexlify
import json
from datetime import datetime
import influxdb
from influxdb import InfluxDBClient

from pprint import pprint
#import requests as req # für URL request

# Use Bluethooth or Serial
# I dont no why, but Serial and rfcomm bind hci0 is faster then BT via Pyhton
#CONNECT_VIA='BT'   # BT | SERIAL (Serial Default)

# Suchen nach der BT MAC Adresse und
# automatisches erstellen des  RFCOMM Port bei Serieller verbindung.
# Kostet etwas mehr zeit.
Bluetooth_Discover = 'n'	# y / n

# Define InfluxDB
influxDB_host        = 'localhost'
influxDB_port        = 8086
influxDB_user        = 'db_meters'
influxDB_pass        = 'db_meters'
influxDB_db          = 'db_meters'
influxDB_measurement = "Battery"
influxDB_tags        = {'BMS': '1'}

# Define BMS MAC Address (BlueTooth)
BMS_MAC_ADDR = "AA:BB:CC:A1:23:45"
BT_PORT      = 1   # default 1

# Define BMS Connection (Serial Port)
# Manuelles erstellen "rfcomm bind hci0 AA:BB:CC:A1:23:45" via Shell
SERIALPORT = "/dev/rfcomm0"
BAUDRATE = 9600

# Define how many Cells you BMS have
BMS_CELLS=16

# Datasize to get from the BMS (default 140) Byte
size = 256

#######################################################
# MOSFET Status Charge [206:208]
MOSFET_Charge_St = [ "OFF",
                     "ON",
                     "overcharge",
                     "overcurrent",
                     "batt full",
                     "pack overvoltage",
                     "bat overtemp",
                     "MOSFET overtemp",
                     "abnormal current",
                     "bat not detected",
                     "PCB overtemp",
                     "11-undefined",
                     "12-undefined",
                     "Discharge MOSFET abnormality",
                     "14",
                     "Manual off"
                   ]

# MOSFET Status Discharge [208:210]
MOSFET_Discharge_St = [ "OFF",
                        "ON",
                        "cell overdischarge",
                        "overcurrent",
                        "4",
                        "pack overdischarge",
                        "bat overtemp",
                        "MOSFET overtemp",
                        "Abnormal current",
                        "battery is not detected",
                        "PCB overtemp",
                        "charge MOSFET turn on",
                        "shortcircuit",
                        "Discharge MOSFET abnormality",
                        "Start exception",
                        "Manual off"
                    ]

# BALANCING STATUS [210:212]
Bal_St = [ "OFF",
           "limit trigger exceeds",
           "charging v diff too high",
           "overtemp",
           "ACTIVE",
           "5-udef",
           "6-udef",
           "7-udef",
           "8-udef",
           "9-udef",
           "PCB Overtemp"
         ]
#######################################################


# Offset        Function                                            Type    Unit
#  *2 - *2+2
#######################################################################################################
#  0 - 3        Frame Header		                                    0xAA 0x55
#                                                                           0xAA 0xFF
#######################################################################################################
#  4 - 69       Voltage data                                                0.000 V
#######################################################################################################
#  70 - 73      BMS Current                                         int     0.0 A
#######################################################################################################
#  74           Percentage of remaining battery	(State of Carge)    u8
#######################################################################################################
#  75 - 78      Battery physical capacity                           u32     .000000 AH
#######################################################################################################
#  79 - 82      The remaining battery capacity                      u32     .000000 AH
#######################################################################################################
#  83 - 86      Total battery cycle                                 u32     .000AH
#######################################################################################################
#  87 - 90      Accumulated from boot time seconds                  u32     S
#######################################################################################################
#  92           Power Temperature                                   short   degree
#  94           Balance Temperature                                 short   degree
#  96           Cell 1 Temperature                                  short   degree
#  98           Cell 2 Temperature                                  short   degree
#  100          Cell 3 Temperature                                  short   degree
#  102          Cell 4 Temperature                                  short   degree
#######################################################################################################
# 103           DCharge mos tube status flag                        u8      (after analysis)
#######################################################################################################
# 104           ischarge mos tube status flag                       u8      (after analysis)
#######################################################################################################
# 105           Balanced status flag                                u8      (resolved below)
#######################################################################################################
# 106 - 107     Tire length                                         u16     MM
#######################################################################################################
# 108 - 109     The number of pulses per week                       u16     N
#######################################################################################################
# 110           Relay switch                                        u8      does not show
#######################################################################################################
# 111 - 114     Current Power                                       int     W
#######################################################################################################
# 115           Maximum number of monomer strings                   u8      None
#######################################################################################################
# 116 - 117     The highest monomer                    	            u16     0.000V
#######################################################################################################
# 118           Lowest monomer string                               u8      None
#######################################################################################################
# 119 - 120     Lowest monomer                                      u16     0.000V
#######################################################################################################
# 121 - 122     Average	                                            u16     0.000V
#######################################################################################################
# 123           The number of effective batteries                   u8      S
#######################################################################################################
# 124 - 125     Detected discharge tube Voltage between D-S poles   u16     0.0V not to be displayed
#######################################################################################################
# 126 - 127     Discharge MOS transistor driving voltage            u16	    0.0V not display
#######################################################################################################
# 128 - 129     Charging MOS tube driving voltage                   u16     0.0V not display
#######################################################################################################
# 130 - 131     When the detected current is 0, the comparator
#               initial value Control equalization corresponds to
#               1 equalization                                      u16	    is not displayed
#######################################################################################################
# 132 - 135     (1 - 32 bits corresponds to
#                1 - 32 string equalization)
#               corresponds to bit 1 displays the color
#                at the corresponding voltage	                    u32
#######################################################################################################
# 136 - 137     The system log is sent to the serial port data
#               0 - 4: Status
#               5 - 9: Battery number
#               10 - 14: Sequential order
#               15: Charge and discharge (1 discharge, 0 charge)    u16
# 136 - 137	System logs
#######################################################################################################
# 138 - 139	Sum check	                                    2 bytes
#######################################################################################################

# Bluetooth discover
#########################
def BT_discover():
  if 'y' == Bluetooth_Discover:
    # Bluetooth discover
    nearby_devices = bluetooth.discover_devices()
    if BMS_MAC_ADDR not in nearby_devices:
      sys.exit('Error: BMS with MAC Address '+BMS_MAC_ADDR+' not in Range')
    else:
      print ('BMS '+bluetooth.lookup_name( BMS_MAC_ADDR )+' with MAC Address '+BMS_MAC_ADDR+' in Range')
      return ('OK')
  else:
    return ('OK')

# Bluetooth Connector
#########################
def BT_connect():
  # Establish connection and setup serial communication
  try:
    s = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
  except socket.error as msg:
    sys.exit("Error: creating Bluetooth socket: ") + str(msg)

  try:
    s.connect((BMS_MAC_ADDR, BT_PORT))
  except socket.error as msg:
    sys.exit("Error: Bluetooth Connection: ") + str(msg)

  # Send and receive data
  try:
    s.sendall(codecs.decode('DBDB00000000','hex'))
  except socket.error as msg:
    s.close()
    sys.exit("Error: send data: ") + str(msg)
  else:
    time.sleep(2)           # Sleep 2 Sec after Write request
    BMS_DATA = s.recv(size) # Get BMS Data
    s.close()
    return (BMS_DATA)

# Serial Connector
#########################
def Serial_connect():
  if 'y' == Bluetooth_Discover:
    subprocess.run(["rfcomm", "bind", "hci0", BMS_MAC_ADDR])

  try:
    Path(SERIALPORT).resolve(strict=True)
  except FileNotFoundError:
    sys.exit('Error: '+SERIALPORT+' not exist')
  else:
    try:
      ser = serial.Serial(
                          port         = SERIALPORT,
                          baudrate     = BAUDRATE,
                          parity       = serial.PARITY_NONE,
                          stopbits     = serial.STOPBITS_ONE,
                          bytesize     = serial.EIGHTBITS,
                          timeout      = 2,
                        )
      while ser.in_waiting:  # Or: while ser.inWaiting():
        print (ser.readline())

      ser.write(codecs.decode('DBDB00000000','hex'))
      time.sleep(2)             # Sleep 2 Sec after Write request

      BMS_DATA = ser.read(size) # Get BMS Data
#      print ('BMS DATA')
#      print (BMS_DATA)
      ser.close()

      if 'y' == Bluetooth_Discover:
        subprocess.run(["rfcomm", "release", "hci0"])

      return (BMS_DATA)
    except Exception as msg:
      sys.exit("Error: Open serial port: ") + str(msg)

# GET BMS Data from Address
def get_data(BMS_DATA, address1, address2, type=None):
  data = codecs.decode(codecs.encode(BMS_DATA,'hex') [int(address1):int(address2)],'utf8')
  if '' == data:
    print ('Error: get invalid Data for '+ str(type)+' Address: '+'['+str(address1)+':'+str(address2)+']' )
    data = '000000'

  if   'Cell Balacing Status' == type:
    data = struct.unpack('>H',unhexlify(data))[0]
#    try:
#      data = struct.unpack('>H',unhexlify(data))[0]
#    except:
#      data = int('0')
#      pass

  elif 'BMS Voltage' == type:
    data = float(format(struct.unpack('>H',unhexlify(data))[0]*0.1,'.2f'))
#    try:
#      data = float(format(struct.unpack('>H',unhexlify(data))[0]*0.1,'.2f'))
#    except:
#      data = float('0')
#      pass

  elif 'Cell Voltage' == type:
    data = float(format(struct.unpack('>H',unhexlify(data))[0]*0.001,'.3f'))
#    try:
#      data = float(format(struct.unpack('>H',unhexlify(data))[0]*0.001,'.3f'))
#    except:
#      data = float('0')
#      pass

  elif 'BMS Current' == type:
    if int(data,16)>2147483648:
      data = float((-(2*2147483648)+int(data,16))*0.1)
    else:
      data = float(int(data,16)*0.1)

  elif 'Power Watt' == type:
    if int(data,16)>2147483648:
      data = float((-(2*2147483648)+int(data,16)))
    else:
      data = float(int(data,16))

  elif 'Battery physical Ah' == type:
    if int(data,16)>2147483648:
      data = float((-(2*2147483648)+int(data,16))*0.000001)
    else:
      data = float(int(data,16)*0.000001)

  elif 'Battery Remaining Ah' == type:
    if int(data,16)>2147483648:
      data = float((-(2*2147483648)+int(data,16))*0.000001)
    else:
      data = float(int(data,16)*0.000001)

  elif 'Total battery cycle Ah' == type:
    if int(data,16)>2147483648:
      data = float((-(2*2147483648)+int(data,16))*0.0001)
    else:
      data = float(int(data,16)*0.0001)

  else:
    data = int(data,16)

  return data

# Connect to InfluxDB
def InfluxDB_connect(host, port, user, password, database):
  try:
    client = influxdb.InfluxDBClient( host, port, user, password )
    databases = client.get_list_database()
  except influxdb.client.InfluxDBClientError as msg:
    sys.exit('Could not connect to InfluxDB: '+str(msg))
  except Exception as msg:
    sys.exit("Error: %s" % msg)
  else:
    if any(d['name'] == database for d in databases):
      client.switch_database(database)
    else:
      client.create_database(database)
    return client

def InfluxDB_write(client, json_body ):
#  print ( client )
#  print ( json.dumps([json_body]) )
#  client.write_points( json.dumps([json_body]) )
  print ( [json_body] )
  client.write_points( [json_body] )

# Connect Via BT or Serial  (Serial Default)
#########################
current_time = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
if BT_discover() == 'OK':
  try:
    CONNECT_VIA
  except NameError:
    BMS_DATA = Serial_connect()
  else:
    if CONNECT_VIA == 'BT':
      BMS_DATA = BT_connect()
    else:
      BMS_DATA = Serial_connect()

# Create InfluxDB connection
InfluxDB_client = InfluxDB_connect(influxDB_host, influxDB_port, influxDB_user, influxDB_pass, influxDB_db)

metrics = {}
# BMS Voltage [8:12]
metrics[ 'BMS Voltage' ] = get_data(BMS_DATA, 8, 12, 'BMS Voltage')

# Cell_voltage
# Cell 01 [12:16] # Cell 02 [16:20] # Cell 03 [20:24] # Cell 04 [24:28]
# Cell 05 [28:32] # Cell 06 [32:36] # Cell 07 [36:40] # Cell 08 [40:44]
# Cell 09 [44:48] # Cell 10 [48:52] # Cell 11 [52:56] # Cell 12 [56:60]
# Cell 13 [60:64] # Cell 14 [64:68] # Cell 15 [68:72] # Cell 16 [72:76]
Celladdress=int('12')
for cell in range(0,BMS_CELLS):
    json_body = [{ "measurement" : "Battery",
                    "tags" : { "Battery": "1",
                               "Cell": str("{0:0=2d}".format(cell+1))
                             },
                   "time" : current_time,
                   "fields" : { 'Cell Voltage' : get_data(BMS_DATA, int(Celladdress), int(Celladdress+4), 'Cell Voltage') }
             }]
    InfluxDB_client.write_points( json_body )
    Celladdress = int(Celladdress+4)


# BMS Current [140:148]
metrics[ 'BMS Current' ] = get_data(BMS_DATA, 140, 148, 'BMS Current')

# State of Carge [148:150]
metrics[ 'State of Carge' ] = int( get_data(BMS_DATA, 148, 150) )

# Battery physical Ah [150:158]
metrics[ 'Battery physical Ah' ] = get_data(BMS_DATA, 150, 158, 'Battery physical Ah')

# Battery Remaining Ah [158:166]
metrics[ 'Battery Remaining Ah' ] = get_data(BMS_DATA, 158, 166, 'Battery Remaining Ah')

# Total battery cycle Ah [166:174]
metrics[ 'Total battery cycle Ah' ] = get_data(BMS_DATA, 166, 174, 'Total battery cycle Ah')

# Power temperature [184:186]
metrics[ 'BMS Temperature' ] = get_data(BMS_DATA, 184, 186)

# Balance temperature [188:190]
metrics[ 'BMS Balance Temperature' ] = get_data(BMS_DATA, 188, 190)

# Cell 1 temperature [192:194]
metrics[ 'BMS Cell Sensor 1 Temperature' ] = get_data(BMS_DATA, 192, 194)

# Cell 2 temperature [196:198]
metrics[ 'BMS Cell Sensor 2 Temperature' ] = get_data(BMS_DATA, 196, 198)

# Cell 3 temperature [200:202]
#metrics[ 'BMS Cell Sensor 3 Temperature' ] = get_data(BMS_DATA, 200, 202)

# MOSFET Status Charge [206:208]
metrics[ 'Charge MOSFET Status' ] = MOSFET_Charge_St[ get_data(BMS_DATA, 206, 208) ]

# MOSFET Status Discharge [208:210]
metrics[ 'Discharge MOSFET Status' ] = MOSFET_Discharge_St[ get_data(BMS_DATA, 208, 210) ]

# BALANCING STATUS [210:212]
metrics[ 'Balancing Status' ] = Bal_St[ get_data(BMS_DATA, 210, 212) ]

# Power [222:230]
metrics[ 'Power Watt' ] = float( get_data(BMS_DATA, 222, 230, 'Power Watt') )

# Cell Max [232:236]
cell_max_voltage = get_data(BMS_DATA, 232, 236, 'Cell Voltage')
metrics[ 'Cell Max Voltage' ] = cell_max_voltage

# Cell Min [238:242]
cell_min_voltage = get_data(BMS_DATA, 238, 242, 'Cell Voltage')
metrics[ 'Cell Min Voltage' ] = cell_min_voltage

# Cell Diff Voltage
metrics[ 'Cell Diff Voltage' ] = float(cell_max_voltage - cell_min_voltage)

# Cell Avg [242:246]
metrics[ 'Cell Avg Voltage' ] = get_data(BMS_DATA, 242, 246, 'Cell Voltage')

# BALANCING STATUS per Cell [268:272]
CellBalacing = get_data(BMS_DATA, 268, 272, 'Cell Balacing Status')
for cell in range(BMS_CELLS):
    json_body = [{ "measurement" : "Battery",
                    "tags" : { "Battery": "1",
                               "Cell": str("{0:0=2d}".format(cell+1))
                             },
                   "time" : current_time,
                   "fields" : { 'Cell Balance' : CellBalacing>>int(cell)&1 }
             }]
    InfluxDB_client.write_points( json_body )

pprint(metrics)

# Build Json for InfluxDB
#################
json_body = [{ "measurement" : "Battery",
               "tags" : { "Battery": "1" },
               "time" : current_time,
               "fields" : metrics
             }]
InfluxDB_client.write_points( json_body )

#json_body = {}
#json_body['measurement'] = influxDB_measurement
#json_body['tags'] = {}
#json_body['time'] = current_time
#json_body['fields'] = {}

# Write to InfluxDB
#InfluxDB_write(InfluxDB_client, json_body )

