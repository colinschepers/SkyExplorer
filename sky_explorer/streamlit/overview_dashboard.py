import time
from datetime import datetime, timedelta
from operator import attrgetter

import pandas as pd
import streamlit as st

from sky_explorer.airports import AirportException
from sky_explorer.opensky_api import OpenSkyApiException, get_min_time
from sky_explorer.streamlit.map import MapRenderer, MapStyle
from sky_explorer.streamlit.models import AirplaneFilter, AirportFilter
from sky_explorer.streamlit.utils import get_airplanes, get_airports, get_from_session_state
from sky_explorer.utils import sort_by_location, predict_airplanes, round_second


class OverviewDashboard:
    def __init__(self):
        self._airplanes = None
        self._latlon_of_interest = None
        self._map_renderer = MapRenderer()
        self._st_airplanes = None
        self._st_airports = None
        self._st_opensky_api_details = None
        self._airplane_filter = AirplaneFilter()
        self._airport_filter = AirportFilter()

    def __call__(self):
        try:
            airplanes = get_airplanes()
        except OpenSkyApiException as exception:
            st.warning(str(exception))
            return

        try:
            airports = get_airports()
        except AirportException as exception:
            st.warning(str(exception))
            return

        with st.sidebar:
            with st.expander("Playback", expanded=False):
                get_from_session_state("animation_speed", lambda: 0)
                display_time = get_from_session_state("display_time", lambda: round_second(datetime.now()))

                columns = st.columns(5)
                if columns[0].button("⏮", help="Skip backward one minute"):
                    st.session_state.display_time = max(get_min_time(), display_time - timedelta(minutes=1))
                if columns[1].button("⏵", help="Play on normal speed"):
                    st.session_state.animation_speed = 1
                if columns[2].button("⏸", help="Pause the animation"):
                    st.session_state.animation_speed = 0
                if columns[3].button("⏩", help="Play on double speed"):
                    st.session_state.animation_speed = 2
                if columns[4].button("⏭", help="Skip forward one minute"):
                    st.session_state.display_time = min(round_second(datetime.now()),
                                                        display_time + timedelta(minutes=1))

            with st.expander("Settings", expanded=False):
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
                    min_value=0, max_value=10000, value=100, step=1,
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
                    min_value=0, max_value=10000, value=100, step=1,
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

        self._update_airplane_data(st.session_state.display_time)
        airports = self._filter_airports(airports)

        columns = st.columns((0.6, 0.4))
        self.st_title = columns[0].title("Sky Explorer")
        self.st_display_time = columns[1].empty()

        self._map_renderer.draw(map_style, airports)

        st.subheader("Airplanes")
        self._st_airplanes = st.empty()

        st.subheader("Airports")
        st.dataframe(airports)

        if st.session_state.animation_speed == 0:
            display_time = get_from_session_state("display_time", lambda: round_second(datetime.now()))
            self._render_airplanes(display_time)
        else:
            self._update_dashboard_continuously()

    def _render_airplanes(self, display_time: datetime):
        self.st_display_time.markdown(
            f"<h1 style='text-align: right;'>{display_time.strftime('%Y-%m-%d %H:%M:%S')}</h1>",
            unsafe_allow_html=True
        )
        self._map_renderer.update(self._airplanes)
        self._st_airplanes.dataframe(self._airplanes.drop(columns="time_position"))

    def _update_airplane_data(self, display_time: datetime):
        filtered_airplanes = self._filter_airplanes(get_airplanes(display_time))
        self._airplanes = predict_airplanes(filtered_airplanes, display_time)

    def _update_dashboard_continuously(self):
        while True:
            start = datetime.now()

            display_time = get_from_session_state("display_time", lambda: round_second(datetime.now()))
            self._update_airplane_data(display_time)
            self._render_airplanes(display_time)

            animation_speed = get_from_session_state("animation_speed", lambda: 0)
            next_display_time = display_time + timedelta(seconds=animation_speed)

            if datetime.now() - start < timedelta(seconds=1):
                time.sleep((1000000 - datetime.now().microsecond) / 1000000)

            st.session_state.display_time = next_display_time

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
