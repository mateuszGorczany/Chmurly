from folium.plugins import MousePosition
import numpy as np
from constants import DATE_FORMAT
from dateutil.parser import parse as parse_stringtime
import datetime

def add_mouse_position_to_map(map):
    formatter = "function(num) {return L.Util.formatNum(num, 3) + ' º ';};"

    MousePosition(
        position="topright",
        separator=" | ",
        empty_string="NaN",
        lng_first=True,
        num_digits=20,
        prefix="Koordynaty:",
        lat_formatter=formatter,
        lng_formatter=formatter,
    ).add_to(map)

def min_max_coordinates(locations):
    locations = np.array(locations)
    return [locations.max(0).tolist(), locations.min(0).tolist()]

def parse_and_format_date(date):
    return parse_stringtime(date).strftime(DATE_FORMAT)

def parse_time(time_to_parse):
    return datetime.datetime.strptime(time_to_parse, '%H:%M').time()

def beautify_location(location):
    x = location.x + np.random.uniform(0.0001, 10**(-6))
    y = location.y + np.random.uniform(0.0001, 10**(-6))
    return [x,y]