from enum import Enum

import pandas as pd
import pydeck as pdk
import streamlit as st

from sky_explorer.config import CONFIG


class MapStyle(Enum):
    Streets = "satellite-streets-v11"
    Satellite = "satellite-v9"
    Light = "light-v10"
    Dark = "dark-v10"


class MapRenderer:
    def __init__(self):
        self._icon_data = CONFIG["map"]["airplane"]["icon"]
        self._view_state = pdk.ViewState(latitude=0, longitude=0, zoom=1)
        self._icon_layer = pdk.Layer(
            type="IconLayer",
            data=None,
            get_icon="icon_data",
            get_size=1,
            size_scale=25,
            get_angle="angle",
            get_position=["longitude", "latitude"],
            pickable=True
        )
        self._deck = pdk.Deck(
            layers=[self._icon_layer],
            map_style=f"mapbox://styles/mapbox/{MapStyle.Streets.value}",
            initial_view_state=self._view_state,
            tooltip={"text": "{callsign}"}
        )
        self._map = None

    def draw(self, map_style: MapStyle):
        self._deck.map_style = f"mapbox://styles/mapbox/{map_style.value}"
        self._map = st.pydeck_chart(self._deck)

    def update(self, states: pd.DataFrame):
        df = states.assign(icon_data=[self._icon_data] * len(states.index))
        df["angle"] = (360 - df["azimuth"])
        self._icon_layer.data = df[["callsign", "longitude", "latitude", "angle", "icon_data"]]
        self._deck.update()
        self._map.pydeck_chart(self._deck)
