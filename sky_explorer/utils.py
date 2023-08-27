from datetime import datetime, timedelta
from functools import partial
from math import asin, atan2, pi, sin, cos
from typing import Tuple

import numpy as np
import pandas as pd
from haversine import haversine

EARTH_RADIUS = 6371


def _euclidean_distance(data: np.array) -> float:
    return haversine((data[0], data[1]), (data[2], data[3]))


def sort_by_location(df: pd.DataFrame, latlon: Tuple[float, float]) -> pd.DataFrame:
    if len(df):
        df = df.copy()
        input_values = np.c_[df[["latitude", "longitude"]].values, np.full((len(df), 2), latlon)]
        distances = np.apply_along_axis(_euclidean_distance, 1, input_values)
        return df.assign(distance=distances).sort_values(by=["distance"]).drop(columns=["distance"])
    return df


def _predict_next_latlon(data: np.array, time: datetime) -> Tuple[float, float]:
    lat, lon, bearing, velocity, time_position = data
    delta_time = (time - time_position).total_seconds()
    distance = velocity * delta_time / 1000
    lat2 = asin(sin(pi / 180 * lat) * cos(distance / EARTH_RADIUS) + cos(pi / 180 * lat)
                * sin(distance / EARTH_RADIUS) * cos(pi / 180 * bearing))
    lon2 = pi / 180 * lon + atan2(
        sin(pi / 180 * bearing) * sin(distance / EARTH_RADIUS) * cos(pi / 180 * lat),
        cos(distance / EARTH_RADIUS) - sin(pi / 180 * lat) * sin(lat2))
    return 180 / pi * lat2, 180 / pi * lon2


def predict_airplanes(airplanes: pd.DataFrame, time: datetime) -> pd.DataFrame:
    if len(airplanes):
        airplanes = airplanes.copy()
        input_values = airplanes[["latitude", "longitude", "azimuth", "velocity", "time_position"]].values
        airplanes[["latitude", "longitude"]] = np.apply_along_axis(
            partial(_predict_next_latlon, time=time), 1, input_values
        )
    return airplanes


def round_second(timestamp: datetime) -> datetime:
    return timestamp - timedelta(microseconds=timestamp.microsecond)
