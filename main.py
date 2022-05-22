# NOTE: This progrem requires raspi-blinka to be installed. Folow the instructions on adafruits website: https://learn.adafruit.com/circuitpython-on-raspberrypi-linux/installing-circuitpython-on-raspberry-pi
# NOTE: This will also require adafruit-circuitpython-lps2x
# NOTE: Requires https://github.com/neliogodoi/MicroPython-SI1145 to function
# NOTE: Requires `pip3 install adafruit-circuitpython-mcp3xxx`

import Adafruit_DHT
import time
from datetime import datetime
from typing import Tuple
import RPi.GPIO as GPIO

# Circut python imports
import board
import busio
import digitalio
import adafruit_lps2x
from api.src.helpers import WindTracker
import si1145
import adafruit_mcp3xxx.mcp3008 as MCP
from adafruit_mcp3xxx.analog_in import AnalogIn

from api import API, RainTracker, RainEvent
from credentials import STATION_ID, STATION_KEY

rain_tracker = RainTracker()
wind_tracker = WindTracker()

####################################
# Config variables for the program #
####################################

# API information
#
# For credentials, create a new file called credentials.py
# and add the constants STATION_ID and STATION_KEY
UPDATE_FREQ = 2.5  # NOTE: Cannot be any less than 2.5

# Temperature and humidity sensor
TEM_SENSOR_TYPE = Adafruit_DHT.DHT22
TEM_PIN = 4

# Switch sensors
RAIN_PIN = 17
WIND_SPEED_PIN = 27
PRESSURE_CALIBRATION_VALUE = 95

# Wind Direction sensor
WIND_DIR_SELECT_PIN = 0
WIND_DIR_CHANEL = MCP.P0

K = 1000
wind_tracker.load_direction_table([
    [0, 33 * K],
    [22.5, 6.57 * K],
    [45, 8.2 * K],
    [67.5, 891],
    [90, 1 * K],
    [112.5, 688],
    [135, 2.2 * K],
    [157.5, 1.41*K],
    [180, 3.9 * K],
    [202.5, 3.14 * K],
    [225, 16 * K],
    [247.5, 14.12 * K],
    [270, 120 * K],
    [292.5, 42.12 * K],
    [315, 64.9 * K],
    [337.5, 21.88 * K]
])

###################################
# Automagicly generated constants #
###################################

print("Magic constants")

i2c = busio.I2C(board.SCL, board.SDA)
spi = busio.SPI(clock=board.SCK, MISO=board.MISO, MOSI=board.MOSI)

def get_press_sensor() -> adafruit_lps2x.LPS22:
    return adafruit_lps2x.LPS22(i2c)  

# NOTE: If you are using an lps25, modify this line
pressure_sensor = get_press_sensor()

uv_sensor = si1145.SI1145()

adc_cs = digitalio.DigitalInOut(board.D5)
adc = MCP.MCP3008(spi, adc_cs)
dir_raw = AnalogIn(adc, WIND_DIR_CHANEL)

#########################
# Other setup functions #
#########################

print("Setup functions")

GPIO.setmode(GPIO.BCM)
GPIO.setup(RAIN_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(WIND_SPEED_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

#############################
# Data collection functions #
#############################

print("Data collection functions")

# Requires the adafruit DHT library to be installed. Run the
# following command to install it:
# pip3 install --install-option="--force-pi" Adafruit_DHT
def get_tem_and_humid() -> Tuple[float, float]:
    return Adafruit_DHT.read_retry(TEM_SENSOR_TYPE, TEM_PIN)


def get_pressure() -> float:
    return pressure_sensor.pressure + PRESSURE_CALIBRATION_VALUE


def get_uv() -> float:
    # The device returns the UV index miltiplied by 100. 
    return uv_sensor.readUV() / 100

def get_wind_direction():
    voltage = dir_raw.voltage
    resistance = (voltage * 10_000)/(3.3 - voltage)
    return wind_tracker.get_direction(resistance)

def rain_callback(*args):
    """
    This function should be called by a hardware interupt whenever the rain sensor is trigured
    """
    print("Rain event")

    rain_tracker.register_rain(RainEvent(0.2794, datetime.now()))

def wind_callback(*args):
    print("Wind event")
    wind_tracker.add_event(datetime.now(), get_wind_direction())

#############
# Main Loop #
#############

print("Loading api")
api = API(STATION_ID, STATION_KEY).use_realtime(UPDATE_FREQ)

GPIO.add_event_detect(RAIN_PIN, GPIO.FALLING, callback=rain_callback, bouncetime=100)
GPIO.add_event_detect(WIND_SPEED_PIN, GPIO.FALLING, callback=wind_callback, bouncetime=100)

while True:
    humidity, temperature = get_tem_and_humid()
    pressure = get_pressure()
    uv = get_uv()

    res = api.start_request().temperature_celsius(temperature).humidity(
        humidity).pressure_hpa(pressure).uv_index(uv).rain(rain_tracker).wind(wind_tracker).send()
    print("Received " + str(res.status_code) + " " + str(res.text))

    time.sleep(UPDATE_FREQ)
