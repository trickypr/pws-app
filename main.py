# NOTE: This progrem requires raspi-blinka to be installed. Folow the instructions on adafruits website: https://learn.adafruit.com/circuitpython-on-raspberrypi-linux/installing-circuitpython-on-raspberry-pi
# NOTE: This will also require adafruit-circuitpython-lps2x
# NOTE: Requires https://github.com/neliogodoi/MicroPython-SI1145 to function
# NOTE: Requires `pip3 install adafruit-circuitpython-mcp3xxx`

#############################
# Import required libraries #
#############################

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

#########################################
# Initialise trackers for longterm data #
#########################################
# For more information on what each of these
# do, take a look at theor definition in the api
# directory

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

# A table that contians the direction values that are found
# in the datasheet of the wind direction sensors
# https://au.mouser.com/datasheet/2/813/DS_15901_Weather_Meter-2489718.pdf
K = 1000
wind_tracker.load_direction_table([[0, 33 * K], [22.5, 6.57 * K],
                                   [45, 8.2 * K], [67.5, 891], [90, 1 * K],
                                   [112.5, 688], [135, 2.2 * K],
                                   [157.5, 1.41 * K], [180, 3.9 * K],
                                   [202.5, 3.14 * K], [225, 16 * K],
                                   [247.5, 14.12 * K], [270, 120 * K],
                                   [292.5, 42.12 * K], [315, 64.9 * K],
                                   [337.5, 21.88 * K]])

###################################
# Automagicly generated constants #
###################################

# Setup the i2c and SPI data buses. We are using the default
# pins to take advantage of hardware acceleration
i2c = busio.I2C(board.SCL, board.SDA)
spi = busio.SPI(clock=board.SCK, MISO=board.MISO, MOSI=board.MOSI)

# This function has been put here to work around the vscode
# reocmendation engine. It thinks that the LPS22 funciton
# will never return, which will break stuff. This is a hakcy
# workaround
def get_press_sensor() -> adafruit_lps2x.LPS22:
    return adafruit_lps2x.LPS22(i2c)

# See the note above the defintion of this function
pressure_sensor = get_press_sensor()

uv_sensor = si1145.SI1145()

# NOTE: Because circut python doesn't support hardware SPI
# chip select, we have to specify a normal pin to act as
# chip select.
adc_cs = digitalio.DigitalInOut(board.D5)
adc = MCP.MCP3008(spi, adc_cs)
dir_raw = AnalogIn(adc, WIND_DIR_CHANEL)

#########################
# Other setup functions #
#########################

# Specifies the method that hardware pins are mapped to
# python. Touching this will probobly break things
GPIO.setmode(GPIO.BCM)

# Both the rain and wind pin act like switches and are pulled
# high when closed. To stop them from floating and trigguring
# at random, we must enable pull down resistors on each
GPIO.setup(RAIN_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(WIND_SPEED_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

#############################
# Data collection functions #
#############################

# Requires the adafruit DHT library to be installed. Run the
# following command to install it:
# pip3 install --install-option="--force-pi" Adafruit_DHT
def get_tem_and_humid() -> Tuple[float, float]:
    # Uses the adafruit library to pull the temperature from our
    # sensor
    return Adafruit_DHT.read_retry(TEM_SENSOR_TYPE, TEM_PIN)


def get_pressure() -> float:
    # Gets the pressure from the sensor and adds a calabration
    # value which I found by comparing to a commercial pressure
    # sensor I have in my house
    return pressure_sensor.pressure + PRESSURE_CALIBRATION_VALUE


def get_uv() -> float:
    # The device returns the UV index miltiplied by 100.
    return uv_sensor.readUV() / 100


def get_wind_direction():
    # The wind direction is selected using the table that is
    # programmed into the tracker up around like 65. These values
    # take in a resistance and spit out a direction. Before we
    # get a direction, we need to calculate the resistance using
    # the first two lines
    voltage = dir_raw.voltage
    resistance = (voltage * 10_000) / (3.3 - voltage)
    return wind_tracker.get_direction(resistance)


def rain_callback(*args):
    """
    This function should be called by a hardware interupt whenever the rain sensor is trigured
    """

    rain_tracker.register_rain(RainEvent(0.2794, datetime.now()))


def wind_callback(*args):
    # Send a wind event and wind direction to the wind tracker, which will
    # use it to determine the average wind speed
    wind_tracker.add_event(datetime.now(), get_wind_direction())


#############
# Main Loop #
#############

# Prepare a connection with weather underground. This does not
# send anything yet, but it stores the nessisary values
api = API(STATION_ID, STATION_KEY).use_realtime(UPDATE_FREQ)

# Both the rain and wind pins need to be setup as interupts and bind to their
# functions defiend aboive. Note that the bounce time is used to filter out
# the reed switches from jumping back on themselves and causing two registrations
# in quick succession
GPIO.add_event_detect(RAIN_PIN,
                      GPIO.FALLING,
                      callback=rain_callback,
                      bouncetime=100)
GPIO.add_event_detect(WIND_SPEED_PIN,
                      GPIO.FALLING,
                      callback=wind_callback,
                      bouncetime=100)

# The weather station should just loop forever
while True:
    # Get the values from the respective functions above
    humidity, temperature = get_tem_and_humid()
    pressure = get_pressure()
    uv = get_uv()

    # Send the data to the api and print the result to the console for
    # debugging purposes.
    res = api.start_request().temperature_celsius(temperature).humidity(
        humidity).pressure_hpa(pressure).uv_index(uv).rain(rain_tracker).wind(
            wind_tracker).send()
    print("Received " + str(res.status_code) + " " + str(res.text))

    # The weatuer underground api will get unhappy if we send things to
    # regularly, so let there be a small sleep timer.
    time.sleep(UPDATE_FREQ)
