#-*- coding: utf-8 -*-

# 필요한 라이브러리를 불러옵니다.
import spidev
import time
import paho.mqtt.client as mqtt
import serial
import sht85
from PMS7003 import PMS7003


#MQTT 통신설정
mqttc = mqtt.Client()
mqttc.connect("localhost",1883,60)
mqttc.subscribe("outTopic")
mqttc.loop_start()

#구독한 채널에서 오는 데이터를 받기위한 변수 초기화
data1 = " "

#MQTT통신 연결	
def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))

#구독한 채널로부터 메시지 올 시 수신받기 위한 메소드
def on_message(client, userdata, msg):
	 global data1
	 if(msg.topic == "outTopic"):
			data1 = str(msg.payload)
			print(data1)
	
#MQTT 연결, 통신
mqttc.on_connect = on_connect
mqttc.on_message = on_message

# 딜레이 시간 (센서 측정 간격)
delay = 1

# 일산화탄소 ppm 계수 
CO_1_M = 2475.24

# 이산화탄소 ppm 계수, 전압에따른 기울기
CO2_max_v = 0.6670898437499999 		#10000ppm
CO2_max_v_divided = 0.078
CO2_min_v = 1.98515625				#400ppm
CO2_min_v_divided = 0.233
CO2_slope = -0.1418

#CO2_slope = -0.11095204008589839

# MCP3008 채널중 센서에 연결한 채널 설정
CO_vgas_channel = 0
CO_vref_channel = 1
CO2_channel = 2
mq5_channel = 3

# SPI 인스턴스 spi 생성
spi = spidev.SpiDev()

# SPI 통신 시작하기
spi.open(0, 0)

# SPI 통신 속도 설정
spi.max_speed_hz = 100000

# 0 ~ 7 까지 8개의 채널에서 SPI 데이터를 읽어서 반환
def readadc(adcnum):
	if adcnum > 7 or adcnum < 0:
		return -1
	r = spi.xfer2([1, 8 + adcnum << 4, 0])
	data = ((r[1] & 3) << 8) + r[2]
	return data

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

try:
	while True:
		st = " "
		
		ser.flushInput()
		buffer = ser.read(1024)

		PM1_0, PM2_5, PM10_0 = dust.print_serial(buffer)
		t,rh = sht85.read_data()
		
		#PM1_0_fix = f'{PM1_0:3}'
		PM1_0_fix = '{0:05d}'.format(PM1_0)
		PM2_5_fix = '{0:05d}'.format(PM2_5)
		PM10_0_fix = '{0:05d}'.format(PM10_0)
		t_fix = '{0:.2f}'.format(t)
		rh_fix = '{0:.2f}'.format(rh)
		
		st = str(PM1_0_fix)
		st += str(PM2_5_fix)
		st += str(PM10_0_fix)
		st += str(t_fix)
		st += str(rh_fix)
		
		print('Temperature =', t_fix, 'Relative Humidity =', rh_fix, 'PM1.0 = ', 
				PM1_0_fix, 'PM2.5 = ', PM2_5_fix, 'PM10.0 = ', PM10_0_fix)

		mqttc.publish("inTopic", st)
		time.sleep(1)
		# readadc 함수로 ldr_channel의 SPI 데이터를 읽어 저장
		
		'''
		CO_vgas_value = readadc(CO_vgas_channel)
		CO_vref_value = readadc(CO_vref_channel)
		CO2_value = readadc(CO2_channel)
		
		print ("---------------------------------------")
		print('readvol_CO_vgas : ' , CO_vgas_value , ' Voltage:' , 3*CO_vgas_value/1024 )
		print ("---------------------------------------")
		print('readvol_CO_vref : ' , CO_vref_value , ' Voltage:' , 3*CO_vref_value/1024 )
		print('Cx = : ' , CO_1_M*((3*CO_vgas_value/1024)-(3*CO_vref_value/1024)))
		time.sleep(1)
		
		#print ("---------------------------------------")
		CO2_v = 3.3*CO2_value/1024
		CO2_v_di = CO2_v / 8.5
		print('readvol_CO2 : ' , CO2_value , 'voltage:', CO2_v_di)
		time.sleep(1)
		CO2_ppm = pow(10, ((CO2_v_di - 0.079) / CO2_slope + 3.698))
		print(CO2_ppm)
		'''
		

except keyboardInterrupt:
	spi.close()
