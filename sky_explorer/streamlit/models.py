from dataclasses import dataclass
from typing import Set, Tuple

FloatRange = Tuple[float, float]


@dataclass
class AirplaneFilter:
    limit: int = None
    callsign: str = None
    airline: str = None
    origin_countries: Set = None
    longitude: FloatRange = None
    latitude: FloatRange = None
    altitude: FloatRange = None
    velocity: FloatRange = None
    azimuth: FloatRange = None


@dataclass
class AirportFilter:
    limit: int = None
    name: str = None
    countries: Set = None
    longitude: FloatRange = None
    latitude: FloatRange = None
    altitude: FloatRange = None
