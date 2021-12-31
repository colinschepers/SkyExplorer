from enum import Enum
from idlelib import tooltip

import pandas as pd
import pydeck as pdk
import streamlit as st

from sky_explorer.config import CONFIG


class MapStyle(Enum):
    Satellite = "satellite-v9"
    Streets = "satellite-streets-v11"
    Light = "light-v10"
    Dark = "dark-v10"


class MapRenderer:
    def __init__(self):
        self._view_state = pdk.ViewState(latitude=0, longitude=0, zoom=1)
        self._airplane_layer = pdk.Layer(
            type="IconLayer",
            data=None,
            get_icon="icon_data",
            get_size=1,
            size_scale=25,
            get_angle="angle",
            get_position=["longitude", "latitude"],
            pickable=True
        )
        self._airport_layer = pdk.Layer(
            type="IconLayer",
            data=None,
            get_icon="icon_data",
            get_size=1,
            size_scale=25,
            get_position=["longitude", "latitude"],
            pickable=True
        )
        self._deck = pdk.Deck(
            layers=[self._airport_layer, self._airplane_layer],
            map_style=f"mapbox://styles/mapbox/{MapStyle.Satellite.value}",
            initial_view_state=self._view_state,
            tooltip={"text": "{tooltip}"}
        )
        self._map = None

    def draw(self, map_style: MapStyle):
        self._deck.map_style = f"mapbox://styles/mapbox/{map_style.value}"
        self._map = st.pydeck_chart(self._deck)

    def update(self, airplanes: pd.DataFrame, airports: pd.DataFrame):
        self._update_airplanes(airplanes)
        self._update_airports(airports)
        self._deck.update()
        self._map.pydeck_chart(self._deck)

    def _update_airplanes(self, airplanes: pd.DataFrame):
        icon_data = CONFIG["map"]["airplane"]["icon"]
        df = airplanes.assign(icon_data=[icon_data] * len(airplanes.index))
        df["angle"] = (360 - df["azimuth"])
        df = df.rename(columns={"callsign": "tooltip"})
        self._airplane_layer.data = df[["longitude", "latitude", "angle", "icon_data", "tooltip"]]

    def _update_airports(self, airports: pd.DataFrame):
        icon_data = CONFIG["map"]["airport"]["icon"]
        df = airports.assign(icon_data=[icon_data] * len(airports.index))
        df['tooltip'] = df.index
        self._airport_layer.data = df[["longitude", "latitude", "icon_data", "tooltip"]]
