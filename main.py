from api import API
from credentials import STATION_ID, STATION_KEY


api = API(STATION_ID, STATION_KEY)

print(api.start_request().temperature_celsius(25.0).send())