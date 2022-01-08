from dataclasses import dataclass
from typing import Set, Tuple

FloatRange = Tuple[float, float]


@dataclass
class AirplaneFilter:
    callsign: str = None
    origin_countries: Set = None
    longitude: FloatRange = None
    latitude: FloatRange = None
    altitude: FloatRange = None
    velocity: FloatRange = None
    azimuth: FloatRange = None


@dataclass
class AirportFilter:
    name: str = None
    countries: Set = None
    longitude: FloatRange = None
    latitude: FloatRange = None
    altitude: FloatRange = None
