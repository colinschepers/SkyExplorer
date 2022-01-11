from datetime import datetime
from math import asin, atan2, pi, sin, cos
from typing import Tuple

import numpy as np
import pandas as pd
from haversine import haversine

EARTH_RADIUS = 6371


def euclidean_distance(latlon1: Tuple[float, float], latlon2: Tuple[float, float]) -> float:
    return haversine(latlon1, latlon2)


def sort_by_location(df: pd.DataFrame, latlon: Tuple[float, float]) -> pd.DataFrame:
    distances = df[["latitude", "longitude"]] \
        .apply(lambda row: euclidean_distance(tuple(row), latlon), axis=1)
    return df.assign(distance=distances).sort_values(by=["distance"]).drop(columns=["distance"])


def _predict_next_latlon(data: np.array) -> Tuple[float, float]:
    lat, lon, bearing, velocity, time_position = data
    delta_time = (datetime.now() - time_position).total_seconds()
    distance = velocity * delta_time / 1000
    lat2 = asin(sin(pi / 180 * lat) * cos(distance / EARTH_RADIUS) + cos(pi / 180 * lat)
                * sin(distance / EARTH_RADIUS) * cos(pi / 180 * bearing))
    lon2 = pi / 180 * lon + atan2(
        sin(pi / 180 * bearing) * sin(distance / EARTH_RADIUS) * cos(pi / 180 * lat),
        cos(distance / EARTH_RADIUS) - sin(pi / 180 * lat) * sin(lat2))
    return 180 / pi * lat2, 180 / pi * lon2


def predict_airplanes(airplanes: pd.DataFrame) -> pd.DataFrame:
    airplanes = airplanes.copy()
    input_values = airplanes[["latitude", "longitude", "azimuth", "velocity", "time_position"]].values
    airplanes[["latitude", "longitude"]] = np.apply_along_axis(_predict_next_latlon, 1, input_values)
    return airplanes
