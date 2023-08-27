from dataclasses import asdict
from datetime import datetime
from os import environ
from typing import Optional, Callable, TypeVar

import pandas as pd
import streamlit as st
from PIL import Image

import sky_explorer.airlines
import sky_explorer.airplanes
import sky_explorer.airports
from sky_explorer.config import CONFIG
from sky_explorer.opensky_api import OpenSkyApi

T = TypeVar('T')


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


def get_from_session_state(key: str, creator: Callable[[], T]) -> T:
    if key not in st.session_state:
        st.session_state[key] = creator()
    return st.session_state[key]


@st.cache(allow_output_mutation=True, show_spinner=False, ttl=3600)
def get_opensky_api():
    username = environ.get("OPENSKY_USERNAME", None)
    password = environ.get("OPENSKY_PASSWORD", None)
    return OpenSkyApi(username, password)


def get_opensky_api_details() -> pd.DataFrame:
    api_details = asdict(get_opensky_api().api_details)
    return pd.DataFrame(api_details.values(), index=api_details.keys(), columns=["value"]).fillna('')


@st.cache(allow_output_mutation=True, show_spinner=False, ttl=3600)
def _get_airplanes(timestamp: Optional[int] = None) -> pd.DataFrame:
    return sky_explorer.airplanes.get_airplanes(get_opensky_api(), timestamp)


def get_airplanes(timestamp: Optional[datetime] = None) -> pd.DataFrame:
    if not timestamp:
        timestamp = datetime.now()

    unix_timestamp = timestamp.timestamp()
    unix_timestamp -= unix_timestamp % CONFIG["time_resolution"]
    return _get_airplanes(int(unix_timestamp))


def get_airports() -> pd.DataFrame:
    return get_from_session_state("airports", sky_explorer.airports.get_airports)


def get_airlines() -> pd.DataFrame:
    return get_from_session_state("airlines", sky_explorer.airlines.get_airlines)
