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