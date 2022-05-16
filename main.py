import Adafruit_DHT
import time

from api import API
from credentials import STATION_ID, STATION_KEY

####################################
# Config variables for the program #
####################################

# API information
#
# For credentials, create a new file called credentials.py
# and add the constants STATION_ID and STATION_KEY
UPDATE_FREQ = 2.5 # NOTE: Cannot be any less than 2.5

# Temperature and humidity sensor
TEM_SENSOR_TYPE = Adafruit_DHT.DHT22
TEM_PIN = 4

# Requires the adafruit DHT library to be installed. Run the
# following command to install it:
# pip3 install --install-option="--force-pi" Adafruit_DHT
def get_tem_and_humid() -> (float, float):
    return Adafruit_DHT.read_retry(TEM_SENSOR_TYPE, TEM_PIN)

# TODO: Enable rapid updates, the code for this is currently on a
# school raspberry pi that I do not have access to.
api = API(STATION_ID, STATION_KEY)

while True:
    temperature, humidity = get_tem_and_humid()

    res = api.start_request().temperature_celsius(temperature).humidity(humidity).send()
    print(res)

    time.sleep(UPDATE_FREQ)




print(api.start_request().temperature_celsius(25.0).send())
