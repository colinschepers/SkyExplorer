import asyncio
from datetime import datetime, timedelta
from operator import attrgetter

import pandas as pd
import streamlit as st

from sky_explorer.config import CONFIG
from sky_explorer.streamlit.map import MapRenderer, MapStyle
from sky_explorer.streamlit.models import AirplaneFilter, AirportFilter
from sky_explorer.streamlit.utils import get_airplanes, get_airports
from sky_explorer.utils import sort_by_location, predict_airplanes


class OverviewDashboard:
    def __init__(self):
        self._airplanes = None
        self._do_animate = False
        self._latlon_of_interest = None
        self._map_renderer = MapRenderer()
        self._st_airplanes = None
        self._st_airports = None
        self._airplane_filter = AirplaneFilter()
        self._airport_filter = AirportFilter()

    def __call__(self):
        asyncio.run(self._run())

    async def _run(self):
        airplanes = await get_airplanes()
        airports = get_airports()

        with st.sidebar:
            with st.expander("Settings", expanded=False):
                self._do_animate = st.checkbox(
                    label="Animation",
                    value=True,
                    key="do_animate"
                )

                cities_of_interest = list(airports["city"].sort_values().unique())
                city_of_interest = st.selectbox(
                    label="City of interest", key="place_of_interest",
                    options=cities_of_interest,
                    index=cities_of_interest.index("Amsterdam")
                )
                airport_of_interest = airports[airports.city == city_of_interest]
                self._latlon_of_interest = tuple(airport_of_interest[["latitude", "longitude"]].values[0])

                map_style = st.selectbox(
                    label="Map style",
                    options=MapStyle,
                    format_func=attrgetter('name'),
                    key="map_style"
                )

            with st.expander("Filter airplanes", expanded=False):
                self._airplane_filter.limit = st.slider(
                    label="Limit", key="airplane_limit",
                    min_value=0, max_value=10000, value=10000, step=1,
                )
                self._airplane_filter.callsign = st.text_input(
                    label="Callsign", key="airplane_callsign",
                    value="", max_chars=8
                )
                self._airplane_filter.airline = st.text_input(
                    label="Airline", key="airplane_airline",
                    value=""
                )
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
                    min_value=0, max_value=30000, value=(0, 30000), step=1,
                )
                self._airplane_filter.velocity = st.slider(
                    label="Velocity (m/s)", key="airplane_velocity",
                    min_value=0, max_value=500, value=(0, 500), step=1
                )
                self._airplane_filter.azimuth = st.slider(
                    label="Azimuth (decimal degrees)", key="airplane_azimuth",
                    min_value=0, max_value=360, value=(0, 360), step=1,
                )

            with st.expander("Filter airports", expanded=False):
                self._airport_filter.limit = st.slider(
                    label="Limit", key="airport_limit",
                    min_value=0, max_value=10000, value=10000, step=1,
                )
                self._airport_filter.name = st.text_input(label="Name", value="", key="airport_name").lower()
                self._airport_filter.countries = set(st.multiselect(
                    label="Country", key="airport_countries",
                    options=airports["country"].sort_values().unique()
                ))
                self._airport_filter.longitude = st.slider(
                    label="Longitude (decimal degrees)", key="airport_longitude",
                    min_value=-180, max_value=180, value=(-180, 180), step=1,
                )
                self._airport_filter.latitude = st.slider(
                    label="Latitude (decimal degrees)", key="airport_latitude",
                    min_value=-90, max_value=90, value=(-90, 90), step=1
                )
                self._airport_filter.altitude = st.slider(
                    label="Altitude (meters)", key="airport_altitude",
                    min_value=0, max_value=10000, value=(-100, 10000), step=1
                )

        self._airplanes = self._filter_airplanes(airplanes)
        airports = self._filter_airports(airports)

        st.title("Overview")
        self._map_renderer.draw(map_style, airports)
        st.subheader("Airplanes")
        self._st_airplanes = st.empty()
        st.subheader("Airports")
        st.dataframe(airports)

        if self._do_animate:
            await self._update_dashboard_continuously()
        else:
            self._update_airplanes()

    def _update_airplanes(self):
        airplanes = predict_airplanes(self._airplanes)
        self._map_renderer.update(airplanes)
        self._st_airplanes.dataframe(airplanes.drop(columns="time_position"))

    async def _update_airplane_data(self):
        airplanes = await get_airplanes(use_session_state=False)
        self._airplanes = self._filter_airplanes(airplanes)

    async def _update_dashboard_continuously(self):
        delay = CONFIG["map"]["animation_delay_ms"] / 1000
        last_update = datetime.min
        loop = asyncio.get_event_loop()

        while True:
            start = datetime.now()

            if datetime.now() - last_update > timedelta(seconds=CONFIG["data_delay"]):
                last_update = datetime.now()
                loop.create_task(self._update_airplane_data())

            self._update_airplanes()

            elapsed = (datetime.now() - start).microseconds / 1000000
            await asyncio.sleep(max(0.01, delay - elapsed))

    def _filter_airplanes(self, airplanes: pd.DataFrame) -> pd.DataFrame:
        mask = (airplanes['longitude'].between(*self._airplane_filter.longitude)) & \
               (airplanes['latitude'].between(*self._airplane_filter.latitude)) & \
               (airplanes['baro_altitude'].between(*self._airplane_filter.altitude)) & \
               (airplanes['velocity'].between(*self._airplane_filter.velocity)) & \
               (airplanes['azimuth'].between(*self._airplane_filter.azimuth))
        if self._airplane_filter.callsign:
            mask &= airplanes['callsign'].str.contains(self._airplane_filter.callsign, case=False)
        if self._airplane_filter.airline:
            mask &= airplanes['airline'].str.contains(self._airplane_filter.airline, case=False)
        if self._airplane_filter.origin_countries:
            mask &= airplanes['origin_country'].isin(self._airplane_filter.origin_countries)

        return sort_by_location(airplanes[mask], self._latlon_of_interest).head(self._airplane_filter.limit)

    def _filter_airports(self, airports: pd.DataFrame) -> pd.DataFrame:
        mask = (airports['longitude'].between(*self._airport_filter.longitude)) & \
               (airports['latitude'].between(*self._airport_filter.latitude)) & \
               (airports['altitude'].between(*self._airport_filter.altitude))
        if self._airport_filter.name:
            mask &= airports['name'].str.normalize('NFKD').str.encode('ascii', errors='ignore').str \
                .decode('utf-8').str.contains(self._airport_filter.name, case=False)
        if self._airport_filter.countries:
            mask &= airports['country'].isin(self._airport_filter.countries)

        return sort_by_location(airports[mask], self._latlon_of_interest).head(self._airport_filter.limit)
