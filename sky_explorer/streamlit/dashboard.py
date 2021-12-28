import asyncio
from operator import attrgetter

import pandas as pd
import streamlit as st

from sky_explorer.config import CONFIG
from sky_explorer.opensky_api import OpenSkyApi
from sky_explorer.streamlit.map import MapRenderer, MapStyle


@st.cache(allow_output_mutation=True, show_spinner=False)
def get_open_sky_api():
    return OpenSkyApi()


@st.cache(allow_output_mutation=True, show_spinner=False, ttl=CONFIG["refresh_delay"])
def get_states():
    return get_open_sky_api().get_states()


class Dashboard:
    def __init__(self):
        self._st_dataframe = None
        self._map_renderer = MapRenderer()
        self._callsign = None
        self._origin_countries = None
        self._longitude = None
        self._latitude = None
        self._altitude = None
        self._velocity = None

    def run(self):
        states = get_states()

        with st.sidebar:
            st.header("Filters")
            self._callsign = st.text_input(label="Callsign", value="", max_chars=8, key="callsign").upper()
            self._origin_countries = set(st.multiselect(
                label="Country of origin",
                options=states["origin_country"].sort_values().unique(),
                key="origin_countries"
            ))
            self._longitude = st.slider(label="Longitude (decimal degrees)", min_value=-180, max_value=180,
                                        value=(-180, 1890), step=1, key="longitude")
            self._latitude = st.slider(label="Latitude (decimal degrees)", min_value=-90, max_value=90,
                                       value=(-90, 90), step=1, key="latitude")
            self._altitude = st.slider(label="Altitude (meters)", min_value=0, max_value=30000,
                                       value=(0, 30000), step=100, key="altitude")
            self._velocity = st.slider(label="Velocity (m/s)", min_value=0, max_value=500,
                                       value=(0, 500), step=10, key="velocity")
            self._azimuth = st.slider(label="Azimuth (decimal degrees)", min_value=0, max_value=360,
                                      value=(0, 360), step=1, key="azimuth")

            st.header("Settings")
            live_view = st.checkbox(
                label="Live view",
                value=True,
                key="live_view"
            )

            map_style = st.selectbox(
                label="Map style",
                options=MapStyle,
                format_func=attrgetter('name'),
                key="map_style"
            )

        st.title("Sky Explorer")
        self._st_dataframe = st.empty()
        self._map_renderer.draw(map_style)

        if live_view:
            asyncio.run(self._update_continuously())
        else:
            self._update(states)

    def _update(self, states: pd.DataFrame):
        mask = (states['longitude'].between(*self._longitude)) & \
               (states['latitude'].between(*self._latitude)) & \
               (states['baro_altitude'].between(*self._altitude)) & \
               (states['velocity'].between(*self._velocity)) & \
               (states['azimuth'].between(*self._azimuth))
        if self._callsign:
            mask &= states['callsign'].str.contains(self._callsign)
        if self._origin_countries:
            mask &= states['origin_country'].isin(self._origin_countries)

        states = states[mask]
        self._st_dataframe.dataframe(states)
        self._map_renderer.update(states)

    async def _update_continuously(self):
        placeholder = st.empty()
        while True:
            self._update(get_states())
            for _ in range(CONFIG["refresh_delay"]):
                # Allow this thread to be killed by streamlit by calling streamlit code
                placeholder.empty()
                await asyncio.sleep(1)
