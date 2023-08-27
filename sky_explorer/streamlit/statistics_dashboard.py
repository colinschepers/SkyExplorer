import asyncio

import streamlit as st
from pandas_profiling import ProfileReport
from streamlit_pandas_profiling import st_profile_report

from sky_explorer.streamlit.utils import get_airplanes, get_airports, get_from_session_state, \
    get_opensky_api_details

_PROFILE_REPORT_KWARGS = {"dark_mode": True, "interactions": None, "correlations": None}


class StatisticsDashboard:
    def __call__(self):
        asyncio.run(self._run())

    async def _run(self):
        st.title("Statistics")
        st.subheader("OpenSky API")
        st.dataframe(get_opensky_api_details())
        st.subheader("Airplanes")
        st_profile_report(get_from_session_state("airplane_report", self.get_airplane_report))
        st.subheader("Airports")
        st_profile_report(get_from_session_state("airport_report", self.get_airport_report))

    @staticmethod
    def get_airplane_report():
        return ProfileReport(get_airplanes(), **_PROFILE_REPORT_KWARGS)

    @staticmethod
    def get_airport_report():
        return ProfileReport(get_airports(), **_PROFILE_REPORT_KWARGS)
