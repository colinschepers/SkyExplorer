from typing import Tuple

import pandas as pd
from haversine import haversine


def euclidean_distance(latlon1: Tuple[float, float], latlon2: Tuple[float, float]):
    return haversine(latlon1, latlon2)


def sort_by_location(df: pd.DataFrame, latlon: Tuple[float, float]):
    df["distance"] = df[["latitude", "longitude"]] \
        .apply(lambda row: euclidean_distance(tuple(row), latlon), axis=1)
    return df.sort_values(by=["distance"]).drop(columns=["distance"])
