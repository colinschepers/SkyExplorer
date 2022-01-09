import asyncio
from operator import attrgetter

import pandas as pd
import streamlit as st

from sky_explorer.config import CONFIG
from sky_explorer.streamlit.map import MapRenderer, MapStyle
from sky_explorer.streamlit.models import AirplaneFilter, AirportFilter
from sky_explorer.streamlit.utils import get_airplanes, get_airports
from sky_explorer.utils import sort_by_location


class OverviewDashboard:
    def __init__(self):
        self._do_update_continuously = False
        self._latlon_of_interest = None
        self._map_renderer = MapRenderer()
        self._st_airplanes = None
        self._st_airports = None
        self._airplane_filter = AirplaneFilter()
        self._airport_filter = AirportFilter()

    def __call__(self):
        airplanes = get_airplanes()
        airports = get_airports()

        with st.sidebar:
            with st.expander("Settings", expanded=False):
                self._do_update_continuously = st.checkbox(
                    label="Update continuously",
                    value=False,
                    key="_do_update_continuously"
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
                    min_value=0, max_value=10000, value=10000, step=100,
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
                self._airport_filter.limit = st.slider(
                    label="Limit", key="airport_limit",
                    min_value=0, max_value=10000, value=10000, step=100,
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
                    min_value=0, max_value=10000, value=(-100, 10000), step=100
                )

        st.title("Overview")
        self._map_renderer.draw(map_style)
        st.subheader("Airplanes")
        self._st_airplanes = st.empty()
        st.subheader("Airports")
        self._st_airports = st.empty()

        if self._do_update_continuously:
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
        airplanes = get_airplanes(use_cache=not self._update_continuously)

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
        airplanes = airplanes[mask]

        return sort_by_location(airplanes, self._latlon_of_interest).head(self._airplane_filter.limit)

    def get_filtered_airports(self) -> pd.DataFrame:
        airports = get_airports()

        mask = (airports['longitude'].between(*self._airport_filter.longitude)) & \
               (airports['latitude'].between(*self._airport_filter.latitude)) & \
               (airports['altitude'].between(*self._airport_filter.altitude))
        if self._airport_filter.name:
            mask &= airports['name'].str.normalize('NFKD').str.encode('ascii', errors='ignore').str \
                .decode('utf-8').str.contains(self._airport_filter.name, case=False)
        if self._airport_filter.countries:
            mask &= airports['country'].isin(self._airport_filter.countries)
        airports = airports[mask]

        return sort_by_location(airports, self._latlon_of_interest).head(self._airport_filter.limit)
