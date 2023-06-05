# -*- coding: utf-8 -*-
"""
Created on Mon Apr 17  23:20:00 2023

@author: rhermsen

Description:
    Python script to obtain the outdoor relative humidity for Nijmegen as a string.
    The output will be used by PM-monitor which expects a JSON formatted output with a timestamp, sensor model, sensor_id and the humidity value.

ToDo:
    - Verify what is the current timeout?.
    - a specific debug option might also be an option.
Done:
    - add a try except error handling for e.g. timeouts.
"""
#Obtain Outdoor Humidity

import requests
from datetime import datetime


def get_humidity():
    """Obtain the outdoor humidity value for Nijmegen from openweathermap.org via API"""

    url ='https://api.openweathermap.org/data/2.5/weather'
    api_key = 'revoked'
    city = 'Nijmegen'

    querystring = {"q":city, 'appid':api_key, 'units':'metric'}

    #Call API
    try:
        response = requests.request("GET", url, params=querystring)
        response = response.json()
    except Exception as e:
        return None
    else:
        humidity = str(response['main']['humidity'])
        return humidity


def get_humidity_buienradar():
    url = 'https://data.buienradar.nl/2.0/feed/json'
    
    #Call API
    try:
        response = requests.request("GET", url)
        response = response.json()
    except Exception as e:
        #print("ErrorType : {}, Error : {}".format(type(e).__name__, e))
        return None
    else:
        humidity = str(response['actual']['stationmeasurements'][1]['humidity'])
        return humidity


def get_message2(timeout=30):
    """Use outdoor humidity to construct a message for futher processing.
    
    Returns
    -------
    Message as a dict, or None if no message is obtained from the API.
    """
    outdoor_rh = get_humidity_buienradar()
    message_dict = {}

    if outdoor_rh != None:
        #construct timestamp
        message_dict["time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message_dict["model"] = "Outdoor Humidity"
        message_dict["id"] = 110
        message_dict["humidity"] = outdoor_rh
        return message_dict
    else:
        return None
#print(get_humidity())
#print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
#print(get_message2())
