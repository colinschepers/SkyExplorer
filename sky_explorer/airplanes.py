from sky_explorer.airlines import get_airlines
from sky_explorer.opensky_api import OpenSkyApi


def get_airplanes():
    airplanes = OpenSkyApi().get_airplanes()
    airlines = get_airlines()
    airlines_col = airplanes["callsign"].apply(lambda callsign: airlines.name.get(callsign[:3], ""))
    airplanes.insert(1, 'airline', airlines_col)
    return airplanes
