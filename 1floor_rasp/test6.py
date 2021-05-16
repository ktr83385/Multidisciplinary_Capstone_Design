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

#이산화 탄소 400이하 값 처리
def CO2_ppm_min(co2_ppm):
  if co2_ppm < 400:
    co2_ppm = 400
  return co2_ppm

#일산화 탄소 음수 처리
def CO_ppm_positive(co_ppm):
  if co_ppm < 0:
    co_ppm = 0
  return co_ppm

#온도에 따른 co값 적용

def CO_temp_ppm(temp, co_ppm):
  if temp <= -16:
    rate = 1*( temp +16 ) + 73
  elif temp <= -4:
    rate = 0.916667*( temp +4 ) + 84
  elif temp <= 8:
    rate = 0.75*( temp - 8 ) + 93
  elif temp <= 20:
    rate = 0.583333*( temp - 20 ) + 100
  elif temp <= 36:
    rate = 0.3125*( temp - 36 ) + 105
  else:
    rate = 0.214286*( temp - 50 ) + 108
  return co_ppm*rate

#온도에 따른 co2값 적용

def CO2_temp_v(temp, co2_v):
  if temp <= 0:
    co2_v = 0.1*( temp ) + 338.2
  elif temp <= 10:
    co2_v = 0.18*( temp - 10 ) + 340
  elif temp <= 20:
    co2_v = 0.14*( temp - 20 ) + 341.4
  elif temp <= 30:
    co2_v = 0.16*( temp - 30 ) + 343
  else:
    co2_v = 0.14*( temp - 50 ) + 345.8
  return co2_v

#습도에 따른 co2값 적용

def CO2_hum_v(hum, co2_v):
  if hum <= 40:
    co2_v = -0.025*( hum - 40 ) + 350.3
  elif hum <= 65.5:
    co2_v = -0.01961*( hum - 65.5 ) + 349.8
  else:
    co2_v = -0.12308*( hum - 85 ) + 347.4
  return co2_v

#전압에 따른 풍속 출력

def wind_speed( vdc):
  speed = 0
  if vdc <= 0.5:
    speed = 0
  elif vdc <= 0.7:
    speed = 0.266667(vdc - 0.7) + 0.75
  elif vdc <= 0.7:
    speed = 0.546667(vdc - 1.11) + 1.5
  elif vdc <= 1.58:
    speed = 0.546667(vdc - 1.58) + 2.25
  else:
    speed = 0.56(vdc - 2) + 3
  return speed

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
		
		#CO_ppm = CO_1_M*((3*CO_vgas_value/1024)-(3*CO_vref_value/1024))
        CO_ppm = CO_ppm_positive(CO_temp_ppm(temp, CO_1_M * ((3 * CO_vgas_value / 1024) - (3 * CO_vref_value / 1024))))#온도 고려

		
		CO2_v = 3.3*CO2_value/1024
		CO2_v_di = CO2_v / 8.5
        CO2_v_di = CO2_hum_v(humi, CO2_temp_v(temp,CO2_v_di))#온습도 고려

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
