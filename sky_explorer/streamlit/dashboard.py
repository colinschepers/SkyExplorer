import asyncio

import pandas as pd
import streamlit as st

from sky_explorer.config import CONFIG
from sky_explorer.opensky_api import OpenSkyApi
from sky_explorer.streamlit.map import MapRenderer


@st.cache(allow_output_mutation=True, show_spinner=False)
def get_open_sky_api():
    return OpenSkyApi()


@st.cache(allow_output_mutation=True, show_spinner=False, ttl=CONFIG["refresh_delay"])
def get_states():
    return get_open_sky_api().get_states()


class Dashboard:
    def __init__(self):
        self._map_renderer = MapRenderer()
        self._st_dataframe = None
        self._callsign = None
        self._origin_countries = []
        self._should_update_continuously = True

    def run(self):
        states = get_states()
        self.render_sidebar(states)

        st.title("Sky Explorer")
        self._st_dataframe = st.empty()
        self._map_renderer.draw()
        self._update(states)

        if self._should_update_continuously:
            asyncio.run(self._update_continuously())

    def render_sidebar(self, states: pd.DataFrame):
        with st.sidebar:
            st.subheader("Filters")
            self._callsign = st.text_input(label="Callsign", value="", max_chars=8, key="callsign").upper()
            self._origin_countries = set(st.multiselect(
                label="Country of origin",
                options=states["origin_country"].sort_values().unique(),
                key="origin_countries"
            ))

            st.subheader("Settings")
            self._should_update_continuously = st.checkbox("Update continuously", value=True,
                                                           key="_should_update_continuously")

    def _update(self, states: pd.DataFrame):
        if self._callsign:
            states = states[states['callsign'].str.contains(self._callsign)]
        if self._origin_countries:
            states = states[states['origin_country'].isin(self._origin_countries)]
        self._st_dataframe.dataframe(states)
        self._map_renderer.update(states)

    async def _update_continuously(self):
        while True:
            await asyncio.sleep(CONFIG["refresh_delay"])
            self._update(get_states())