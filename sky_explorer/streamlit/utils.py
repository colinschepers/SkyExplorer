from typing import Optional

import pandas as pd
import streamlit as st
from PIL import Image

import sky_explorer.airplanes
import sky_explorer.airports
import sky_explorer.airlines
from sky_explorer.config import CONFIG


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
def _get_airplanes() -> Optional[pd.DataFrame]:
    return sky_explorer.airplanes.get_airplanes()


def get_airplanes(use_cache: bool = False) -> pd.DataFrame:
    if "airplanes" not in st.session_state or not use_cache:
        st.session_state["airplanes"] = _get_airplanes()
    return st.session_state["airplanes"]


def get_airports() -> pd.DataFrame:
    if "airports" not in st.session_state:
        st.session_state["airports"] = sky_explorer.airports.get_airports()
    return st.session_state["airports"]


def get_airlines() -> pd.DataFrame:
    if "airlines" not in st.session_state:
        st.session_state["airlines"] = sky_explorer.airlines.get_airlines()
    return st.session_state["airlines"]
