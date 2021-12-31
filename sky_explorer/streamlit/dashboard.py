import asyncio
from operator import attrgetter

import pandas as pd
import streamlit as st

from sky_explorer.config import CONFIG
from sky_explorer.streamlit.map import MapRenderer, MapStyle
from sky_explorer.streamlit.models import AirplaneFilter, AirportFilter
from sky_explorer.streamlit.utils import get_airplanes, get_airports
from sky_explorer.utils import get_country_name


class Dashboard:
    def __init__(self):
        self._map_renderer = MapRenderer()
        self._st_airplanes = None
        self._st_airports = None
        self._airplane_filter = AirplaneFilter()
        self._airport_filter = AirportFilter()

    def run(self):
        airplanes = get_airplanes()
        airports = get_airports()

        with st.sidebar:
            with st.expander("Settings", expanded=False):
                live_view = st.checkbox(
                    label="Live view",
                    value=False,
                    key="live_view"
                )

                map_style = st.selectbox(
                    label="Map style",
                    options=MapStyle,
                    format_func=attrgetter('name'),
                    key="map_style"
                )

            with st.expander("Filter airplanes", expanded=False):
                self._airplane_filter.callsign = st.text_input(label="Callsign", value="", max_chars=8,
                                                               key="airplane_callsign").upper()
                self._airplane_filter.origin_countries = set(st.multiselect(
                    label="Country of origin", key="airplane_origin_countries",
                    options=airplanes["origin_country"].sort_values().unique(),
                ))
                self._airplane_filter.longitude = st.slider(
                    label="Longitude (decimal degrees)", key="airplane_longitude",
                    min_value=-180, max_value=180, value=(-180, 180), step=1,
                )
                self._airplane_filter.latitude = st.slider(
                    label="Latitude (decimal degrees)", key="airplane_latitude",
                    min_value=-90, max_value=90, value=(-90, 90), step=1
                )
                self._airplane_filter.altitude = st.slider(
                    label="Altitude (meters)", key="airplane_altitude",
                    min_value=0, max_value=30000, value=(0, 30000), step=100,
                )
                self._airplane_filter.velocity = st.slider(
                    label="Velocity (m/s)", key="airplane_velocity",
                    min_value=0, max_value=500, value=(0, 500), step=10
                )
                self._airplane_filter.azimuth = st.slider(
                    label="Azimuth (decimal degrees)", key="airplane_azimuth",
                    min_value=0, max_value=360, value=(0, 360), step=1,
                )

            with st.expander("Filter airports", expanded=False):
                self._airport_filter.name = st.text_input(label="Name", value="", key="airport_name").lower()
                self._airport_filter.countries = set(st.multiselect(
                    label="Country", key="airport_countries",
                    options=airports["country"].sort_values(key=lambda x: x.apply(get_country_name)).unique(),
                    format_func=get_country_name
                ))
                self._airport_filter._type = set(st.multiselect(
                    label="Type", key="airport_type",
                    options=airports["type"].sort_values().unique(),
                    format_func=lambda x: x.replace('_', ' ').capitalize(),
                ))
                self._airport_filter.longitude = st.slider(
                    label="Longitude (decimal degrees)", key="airport_longitude",
                    min_value=-180, max_value=180, value=(-180, 180), step=1,
                )
                self._airport_filter.latitude = st.slider(
                    label="Latitude (decimal degrees)", key="airport_latitude",
                    min_value=-90, max_value=90, value=(-90, 90), step=1
                )
                self._airport_filter.elevation = st.slider(
                    label="Elevation (meters)", key="airport_elevation",
                    min_value=0, max_value=10000, value=(-100, 10000), step=100
                )

        st.title("Sky Explorer")
        self._map_renderer.draw(map_style)
        st.subheader("Airplanes")
        self._st_airplanes = st.empty()
        st.subheader("Airports")
        self._st_airports = st.empty()

        if live_view:
            asyncio.run(self._update_continuously())
        else:
            self._update()

    def _update(self):
        airplanes = self.get_filtered_airplanes()
        airports = self.get_filtered_airports()
        self._map_renderer.update(airplanes, airports)
        self._st_airplanes.dataframe(airplanes)
        self._st_airports.dataframe(airports)

    async def _update_continuously(self):
        placeholder = st.empty()
        while True:
            self._update()
            for _ in range(CONFIG["refresh_delay"]):
                # Allow this thread to be killed by streamlit by calling streamlit code
                placeholder.empty()
                await asyncio.sleep(1)

    def get_filtered_airplanes(self) -> pd.DataFrame:
        df = get_airplanes()
        mask = (df['longitude'].between(*self._airplane_filter.longitude)) & \
               (df['latitude'].between(*self._airplane_filter.latitude)) & \
               (df['baro_altitude'].between(*self._airplane_filter.altitude)) & \
               (df['velocity'].between(*self._airplane_filter.velocity)) & \
               (df['azimuth'].between(*self._airplane_filter.azimuth))
        if self._airplane_filter.callsign:
            mask &= df['callsign'].str.contains(self._airplane_filter.callsign)
        if self._airplane_filter.origin_countries:
            mask &= df['origin_country'].isin(self._airplane_filter.origin_countries)
        return df[mask]

    def get_filtered_airports(self) -> pd.DataFrame:
        df = get_airports()
        mask = (df['longitude'].between(*self._airport_filter.longitude)) & \
               (df['latitude'].between(*self._airport_filter.latitude)) & \
               (df['elevation'].between(*self._airport_filter.elevation))
        if self._airport_filter.name:
            mask &= df['name'].str.contains(self._airport_filter.name)
        if self._airport_filter.countries:
            mask &= df['country'].isin(self._airport_filter.countries)
        if self._airport_filter.type:
            mask &= df['type'].isin(self._airport_filter.type)
        return df[mask]
