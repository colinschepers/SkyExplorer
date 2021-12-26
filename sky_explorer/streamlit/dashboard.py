import asyncio

import streamlit as st
from PIL import Image

from sky_explorer.config import CONFIG
from sky_explorer.opensky_api import CachedOpenSkyApi
from sky_explorer.streamlit.map import MapRenderer

st.set_page_config(
    page_title="Sky Explorer",
    page_icon=Image.open("favicon.ico"),
    layout="wide"
)
st.markdown(
    """
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True
)


@st.cache(allow_output_mutation=True)
def get_open_sky_api():
    return CachedOpenSkyApi()


class Dashboard:
    def __init__(self):
        self._open_sky_api = get_open_sky_api()
        self._states = self._open_sky_api.get_states()
        self._map_renderer = MapRenderer()
        self._refresh_delay = CONFIG["refresh_delay"]

    def run(self):
        st.title("Sky Explorer")

        st.dataframe(self._states)

        self._map_renderer.draw(self._states)
        asyncio.run(self._update())

    async def _update(self):
        while True:
            states = self._open_sky_api.get_states()
            self._map_renderer.update(states)
            await asyncio.sleep(self._refresh_delay)
