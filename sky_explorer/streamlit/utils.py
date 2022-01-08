from typing import Optional

import pandas as pd
import streamlit as st
from PIL import Image

import sky_explorer.airports
import sky_explorer.airlines
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


@st.cache(allow_output_mutation=True, show_spinner=False, ttl=CONFIG["refresh_delay"])
def get_airplanes() -> Optional[pd.DataFrame]:
    return OpenSkyApi().get_airplanes()


def get_airports() -> pd.DataFrame:
    if "airports" not in st.session_state:
        st.session_state.airports = sky_explorer.airports.get_airports()
    return st.session_state.airports
