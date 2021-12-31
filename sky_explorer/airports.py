import argparse
import os
from pathlib import Path

import pandas as pd

from sky_explorer.config import CONFIG


class AirportProvider:
    def __init__(self):
        self.airports = self._load_airports()

    @staticmethod
    def _load_airports():
        path = Path(CONFIG["data_dir"]) / "airports.csv"
        if not path.exists():
            df = pd.read_csv("http://ourairports.com/data/airports.csv")
            columns = {"ident": "icao", "type": "type", "name": "name", "latitude_deg": "latitude",
                       "longitude_deg": "longitude", "elevation_ft": "elevation", "iso_country": "country"}
            df = df[df.scheduled_service == "yes"]
            df = df[columns.keys()].rename(columns=columns).set_index("icao")
            df[["latitude", "longitude"]] = df[["latitude", "longitude"]].fillna(0)
            df = df.dropna()
            df = df.astype({"elevation": int})
            os.makedirs(CONFIG["data_dir"], exist_ok=True)
            df.to_csv(path)
        return pd.read_csv(path).set_index("icao")
