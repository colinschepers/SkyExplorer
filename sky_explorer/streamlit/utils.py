from datetime import datetime

import pandas as pd
import streamlit as st
from PIL import Image

import sky_explorer.airlines
import sky_explorer.airplanes
import sky_explorer.airports
from sky_explorer.config import CONFIG
from sky_explorer.streamlit.caching import GLOBAL_CACHE


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


async def _get_airplanes() -> pd.DataFrame:
    if (datetime.now() - GLOBAL_CACHE.get("airplanes_last_query_time", datetime.min)).seconds > CONFIG["data_delay"]:
        airplanes = await sky_explorer.airplanes.get_airplanes()
        if airplanes is not None:
            GLOBAL_CACHE["airplanes_last_query_time"] = datetime.now()
            GLOBAL_CACHE["airplanes"] = airplanes
    return GLOBAL_CACHE["airplanes"].copy()


async def get_airplanes(use_session_state: bool = True) -> pd.DataFrame:
    if "airplanes" not in st.session_state or not use_session_state:
        st.session_state["airplanes"] = await _get_airplanes()
    return st.session_state["airplanes"]


def get_airports() -> pd.DataFrame:
    if "airports" not in st.session_state:
        st.session_state["airports"] = sky_explorer.airports.get_airports()
    return st.session_state["airports"]


def get_airlines() -> pd.DataFrame:
    if "airlines" not in st.session_state:
        st.session_state["airlines"] = sky_explorer.airlines.get_airlines()
    return st.session_state["airlines"]
