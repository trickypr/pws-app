# NOTE: This progrem requires raspi-blinka to be installed. Folow the instructions on adafruits website: https://learn.adafruit.com/circuitpython-on-raspberrypi-linux/installing-circuitpython-on-raspberry-pi
# NOTE: This will also require adafruit-circuitpython-lps2x
# NOTE: Requires https://github.com/neliogodoi/MicroPython-SI1145 to function

import Adafruit_DHT
import time
from datetime import datetime
from typing import Tuple
import RPi.GPIO as GPIO

# Circut python imports
import board
import busio
import adafruit_lps2x
import si1145

from api import API, RainTracker, RainEvent
from credentials import STATION_ID, STATION_KEY

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

# Rain sensor
RAIN_PIN = 16

###################################
# Automagicly generated constants #
###################################

i2c = busio.I2C(board.SCL, board.SDA)
pressure_sensor = adafruit_lps2x.LPS22(
    i2c)  # NOTE: If you are using an lps25, modify this line
uv_sensor = si1145.SI1145(i2c=i2c)

rain_tracker = RainTracker()

#########################
# Other setup functions #
#########################

GPIO.setmode(GPIO.BCM)
GPIO.setup(RAIN_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)


#############################
# Data collection functions #
#############################


# Requires the adafruit DHT library to be installed. Run the
# following command to install it:
# pip3 install --install-option="--force-pi" Adafruit_DHT
def get_tem_and_humid() -> Tuple[float, float]:
    return Adafruit_DHT.read_retry(TEM_SENSOR_TYPE, TEM_PIN)


def get_pressure() -> float:
    return pressure_sensor.pressure


def get_uv() -> float:
    return uv_sensor.read_uv

def rain_callback():
    """
    This function should be called by a hardware interupt whenever the rain sensor is trigured
    """

    rain_tracker.register_rain(RainEvent(0.2794, datetime.now()))

#############
# Main Loop #
#############

# TODO: Enable rapid updates, the code for this is currently on a
# school raspberry pi that I do not have access to.
api = API(STATION_ID, STATION_KEY).use_realtime(UPDATE_FREQ)

GPIO.add_event_detect(RAIN_PIN, GPIO.FALLING, callback=rain_callback, bouncetime=100)

while True:
    temperature, humidity = get_tem_and_humid()
    pressure = get_pressure()
    uv = get_uv()
    rain = rain_tracker.get_past_hour()

    res = api.start_request().temperature_celsius(temperature).humidity(
        humidity).pressure_hpa(pressure).uv_index(uv).hourly_rain_mm(rain).send()
    print(res)

    time.sleep(UPDATE_FREQ)
