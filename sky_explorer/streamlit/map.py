import pandas as pd
import pydeck as pdk
import streamlit as st

from sky_explorer.config import CONFIG


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
            get_angle="azimuth",
            get_position=["longitude", "latitude"],
            pickable=True
        )
        self._deck = pdk.Deck(
            layers=[self._icon_layer],
            map_style="mapbox://styles/mapbox/satellite-v9",
            initial_view_state=self._view_state,
            tooltip={"text": "{callsign}"}
        )
        self._map = None

    def draw(self, states: pd.DataFrame):
        df = states.assign(icon_data=[self._icon_data] * len(states.index))
        self._icon_layer.data = df
        self._deck.update()
        self._map = st.pydeck_chart(self._deck)

    def update(self, states: pd.DataFrame):
        df = states.assign(icon_data=[self._icon_data] * len(states.index))
        self._icon_layer.data = df
        self._deck.update()
        self._map.pydeck_chart(self._deck)
