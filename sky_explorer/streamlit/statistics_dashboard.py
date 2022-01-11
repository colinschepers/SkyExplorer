import asyncio

import streamlit as st
from pandas_profiling import ProfileReport
from streamlit_pandas_profiling import st_profile_report

from sky_explorer.airplanes import get_airplanes
from sky_explorer.airports import get_airports


class StatisticsDashboard:
    def __init__(self):
        pass

    def __call__(self):
        asyncio.run(self._run())

    async def _run(self):
        st.title("Statistics")
        st.subheader("Airplanes")
        st_profile_report(await self.get_airplane_report())
        st.subheader("Airports")
        st_profile_report(self.get_airport_report())

    async def get_airplane_report(self):
        if "airplane_report" not in st.session_state:
            airplanes = await get_airplanes()
            st.session_state["airplane_report"] = ProfileReport(airplanes)
        return st.session_state["airplane_report"]

    def get_airport_report(self):
        if "airport_report" not in st.session_state:
            airports = get_airports()
            st.session_state["airport_report"] = ProfileReport(airports)
        return st.session_state["airport_report"]
