from typing import Optional

import pandas as pd
import streamlit as st
from PIL import Image

from sky_explorer.airports import AirportProvider
from sky_explorer.config import CONFIG
from sky_explorer.opensky_api import OpenSkyApi


def init_page_layout():
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
            .block-container {padding: 1rem;}
        </style>
        """,
        unsafe_allow_html=True
    )


@st.cache(allow_output_mutation=True, show_spinner=False)
def get_airport_provider():
    return AirportProvider()


@st.cache(allow_output_mutation=True, show_spinner=False)
def get_airports() -> pd.DataFrame:
    return get_airport_provider().airports


@st.cache(allow_output_mutation=True, show_spinner=False)
def get_open_sky_api():
    return OpenSkyApi()


@st.cache(allow_output_mutation=True, show_spinner=False, ttl=CONFIG["refresh_delay"])
def get_airplanes() -> Optional[pd.DataFrame]:
    return get_open_sky_api().get_airplanes()
