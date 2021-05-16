#-*- coding: utf-8 -*-

import spidev
import time
import paho.mqtt.client as mqtt
import serial
import sht85
from PMS7003 import PMS7003
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

CO2_ppm		= 0
CO_ppm		= 0

#MQTT setting
mqttc = mqtt.Client()
mqttc.connect("10.90.3.49",1883,60)
mqttc.subscribe("inTopic")
mqttc.loop_start()

#MQTT data
data1 = " "

#MQTT connect
def on_connect(client, userdata, flags, rc):
	print("Connected with result code " + str(rc))

#callback method
def on_message(client, userdata, msg):
	global data1
	if(msg.topic == "inTopic"):
		global CO2_ppm, CO_ppm
		data1 = str(msg.payload)
		
		PM1_0 = int(data1[2:7])
		PM2_5 = int(data1[7:12])
		PM10_0 = int(data1[12:17])
		temp = float(data1[17:22])
		humi = float(data1[22:27])
	
		print(data1)
		print('PM1_0 = ', PM1_0,'PM2_5 = ', PM2_5,'PM10_0 = ', PM10_0,
			'temp = ', temp,'humi = ', humi)
		
		

		CO_vgas_value = readadc(CO_vgas_channel)
		CO_vref_value = readadc(CO_vref_channel)
		CO2_value = readadc(CO2_channel)
		
		CO_ppm = CO_1_M*((3*CO_vgas_value/1024)-(3*CO_vref_value/1024))
		
		CO2_v = 3.3*CO2_value/1024
		CO2_v_di = CO2_v / 8.5
		CO2_ppm = pow(10, ((CO2_v_di - 0.079) / CO2_slope + 3.698))
		
		_point1 = Point("sangrokwon").tag("location", "3_floor").field("PM1.0", PM1_0)
		_point2 = Point("sangrokwon").tag("location", "3_floor").field("PM2.5", PM2_5)
		_point3 = Point("sangrokwon").tag("location", "3_floor").field("PM10.0", PM10_0)
		_point4 = Point("sangrokwon").tag("location", "3_floor").field("Temperature", temp)
		_point5 = Point("sangrokwon").tag("location", "3_floor").field("Humidity", humi)
		_point6 = Point("sangrokwon").tag("location", "1_floor").field("CO2_ppm", CO2_ppm)
		_point7 = Point("sangrokwon").tag("location", "1_floor").field("CO_ppm", CO_ppm)
		write_api.write(bucket=bucket, record=[_point1,_point2,_point3,_point4,_point5,_point6,_point7])
		
		
		print('CO2 ppm = ', CO2_ppm, 'CO ppm = ', CO_ppm)

#MQTT connect, callback
mqttc.on_connect = on_connect
mqttc.on_message = on_message


# 일산화탄소 ppm 계수 
CO_1_M = 2475.24

# 이산화탄소 ppm 계수, 전압에따른 기울기
CO2_max_v = 0.6670898437499999       #10000ppm
CO2_max_v_divided = 0.078
CO2_min_v = 1.98515625            #400ppm
CO2_min_v_divided = 0.233
CO2_slope = -0.1418



#CO2_slope = -0.11095204008589839


CO_vgas_channel = 0
CO_vref_channel = 1
CO2_channel = 2
mq135_channel = 3

spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 100000

def readadc(adcnum):
	if adcnum > 7 or adcnum < 0:
		return -1
	r = spi.xfer2([1, 8 + adcnum << 4, 0])
	data = ((r[1] & 3) << 8) + r[2]
	return data
'''
dust = PMS7003()

# UART / USB Serial : 'dmesg | grep ttyUSB'
USB0 = '/dev/ttyUSB0'
UART = '/dev/ttyAMA0'

# Baud Rate
Speed = 9600

#serial setting 
SERIAL_PORT = USB0
ser = serial.Serial(SERIAL_PORT, Speed, timeout = 1)

mps = 1 # accepted intervals 0.5, 1, 2, 4, 10 seconds
rep = 'HIGH' # Repeatability: HIGH, MEDIUM, LOW

time.sleep(0.5e-3)
sht85.periodic(mps,rep)
time.sleep(1)
'''

bucket = "test"
mytoken = "dLCN0Dt_TXxk4ASzM6rJMaKa9T2Q6MrW65ayAYht-n69TdRVxuXXSQ_yo-pmfOhIElL7FLbveib-0gtBpkuiIA=="
client = InfluxDBClient(url="http://52.79.255.212:8086", 
                token=mytoken, org="test")

write_api = client.write_api(write_options=SYNCHRONOUS)
query_api = client.query_api()

p = Point("test").tag("location", "Prague").field("temperature", 25.3)

write_api.write(bucket=bucket, record=p)

## using Table structure
tables = query_api.query('from(bucket:"test") |> range(start: -10m)')

for table in tables:
    print(table)
    for row in table.records:
        print (row.values)


## using csv library
csv_result = query_api.query_csv('from(bucket:"test") |> range(start: -10m)')
val_count = 0
for row in csv_result:
    for cell in row:
        val_count += 1

try:
	while True:
		
		'''
		print ("---------------------------------------")0
		print('readvol_CO_vgas : ' , CO_vgas_value , ' Voltage:' , 3*CO_vgas_value/1024 )
		print ("---------------------------------------")
		print('readvol_CO_vref : ' , CO_vref_value , ' Voltage:' , 3*CO_vref_value/1024 )
		print('Cx = : ' , CO_1_M*((3*CO_vgas_value/1024)-(3*CO_vref_value/1024)))
		
		
		
		
		#print ("---------------------------------------")
		
		
		
		ser.flushInput()
		buffer = ser.read(1024)
		# print data
		PM1_0, PM2_5, PM10_0 = dust.print_serial(buffer)
		
		t,rh = sht85.read_data()
		print('Temperature =', t)
		print('Relative Humidity =', rh)
		time.sleep(1)

		
		_point1 = Point("test").tag("location", "SW Center").field("CO2_ppm", CO2_ppm)
		_point2 = Point("test").tag("location", "SW Center").field("temperature", t)
		_point3 = Point("test").tag("location", "SW Center").field("Humidity", rh)
		_point4 = Point("test").tag("location", "SW Center").field("PM1.0", PM1_0)
		_point5 = Point("test").tag("location", "SW Center").field("PM2.5", PM2_5)
		_point6 = Point("test").tag("location", "SW Center").field("PM10.0", PM10_0)
		_point7 = Point("test").tag("location", "SW Center").field("CO_ppm", CO_ppm)
		write_api.write(bucket=bucket, record=[_point1,_point2,_point3,_point4,_point5,_point6,_point7])
		
		time.sleep(0.5)
		'''
except KeyboardInterrupt:
	spi.close()
