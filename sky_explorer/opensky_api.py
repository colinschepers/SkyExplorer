import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional, Tuple, Sequence, Dict, Any, Mapping, Callable

import pandas as pd
import requests

LOGGER = logging.getLogger('opensky_api')


class OpenSkyApi:
    """Access to OpenSky REST API, based on packages `opensky_api` and `traffic`.

    The REST API is documented here: https://opensky-network.org/apidoc/rest.html
    """

    BASE_URL = "https://opensky-network.org/api"
    TIME_DIFF_NO_AUTH = 10
    TIME_DIFF_AUTH = 5

    STATE_COLUMNS = {
        "icao24": str,
        "callsign": lambda x: str(x).strip(),
        "origin_country": str,
        "time_position": lambda x: datetime.fromtimestamp(x) if x else None,
        "last_contact": None,
        "longitude": lambda x: float(x) if x else None,
        "latitude": lambda x: float(x) if x else None,
        "baro_altitude": lambda x: float(x) if x else 0,
        "on_ground": None,
        "velocity": lambda x: float(x) if x else 0,
        "azimuth": lambda x: 360 - float(x) if x else None,
        "vertical_rate": None,
        "sensors": None,
        "geo_altitude": None,
        "squawk": None,
        "spi": None,
        "position_source": None,
        "_": None
    }
    TRACK_COLUMNS = ["timestamp", "latitude", "longitude", "altitude", "track", "on_ground"]
    AIRCRAFT_COLUMNS = ["first_seen", "last_seen", "icao24", "callsign", "est_departure_airport", "est_arrival_airport"]

    def __init__(
            self,
            username: Optional[str] = None,
            password: Optional[str] = None
    ) -> None:
        self._auth = (username, password) if username is not None else ()
        self._session = requests.Session()

    def _get_json(self, url_suffix: str, params: Mapping[str, str] = None):
        response = requests.get(f"{self.BASE_URL}{url_suffix}", auth=self._auth, params=params, timeout=15)
        if response.status_code == 200:
            return response.json()
        else:
            LOGGER.debug(f"Response not OK. Status {response.status_code} - {response.reason}")
        return None

    def get_states(
            self,
            time: Optional[datetime] = None,
            icao24: Optional[str] = None,
            bounds: Optional[Tuple[float, float, float, float]] = None,
    ) -> Optional[pd.DataFrame]:
        """Returns the current state vectors from OpenSky REST API.

        Official documentation
        ----------------------
        Limitations for anonymous (unauthenticated) users
        Anonymous are those users who access the API without using credentials.
        The limitations for anonymous users are:
        Anonymous users can only get the most recent state vectors, i.e. the
        time parameter will be ignored.  Anonymous users can only retrieve data
        with a time resolution of 10 seconds. That means, the API will return
        state vectors for time now − (now mod 10)
        Limitations for OpenSky users
        An OpenSky user is anybody who uses a valid OpenSky account (see below)
        to access the API. The rate limitations for OpenSky users are:
        - OpenSky users can retrieve data of up to 1 hour in the past. If the
        time parameter has a value t < now−3600 the API will return
        400 Bad Request.
        - OpenSky users can retrieve data with a time resolution of 5 seconds.
        That means, if the time parameter was set to t , the API will return
        state vectors for time t−(t mod 5).
        """
        params = {"time": int(time.timestamp()) if time is not None else 0, "icao24": icao24}

        if bounds:
            if len(bounds) != 4:
                raise ValueError("Invalid bounding box! Must be "
                                 "[min_latitude, max_latitude, min_longitude, max_latitude]")
            self._check_lat(bounds[0])
            self._check_lat(bounds[1])
            self._check_lon(bounds[2])
            self._check_lon(bounds[3])
            params.update({"lamin": bounds[0], "lamax": bounds[1], "lomin": bounds[2], "lomax": bounds[3]})

        if json := self._get_json("/states/all", params=params):
            data = [self._parse_instance(x, self.STATE_COLUMNS) for x in json["states"]]
            return pd.DataFrame(data).dropna().set_index('icao24')
        return None

    def get_tracks(
            self, icao24: str, time: Optional[datetime] = None
    ) -> Optional[pd.DataFrame]:
        """Returns a Flight corresponding to a given aircraft.

        Official documentation
        ----------------------
        Retrieve the trajectory for a certain aircraft at a given time. The
        trajectory is a list of waypoints containing position, barometric
        altitude, true track and an on-ground flag.
        In contrast to state vectors, trajectories do not contain all
        information we have about the flight, but rather show the aircraft’s
        general movement pattern. For this reason, waypoints are selected among
        available state vectors given the following set of rules:
        - The first point is set immediately after the the aircraft’s expected
        departure, or after the network received the first poisition when the
        aircraft entered its reception range.
        - The last point is set right before the aircraft’s expected arrival, or
        the aircraft left the networks reception range.
        - There is a waypoint at least every 15 minutes when the aircraft is
        in-flight.
        - A waypoint is added if the aircraft changes its track more than 2.5°.
        - A waypoint is added if the aircraft changes altitude by more than 100m
        (~330ft).
        - A waypoint is added if the on-ground state changes.
        Tracks are strongly related to flights. Internally, we compute flights
        and tracks within the same processing step. As such, it may be
        benificial to retrieve a list of flights with the API methods from
        above, and use these results with the given time stamps to retrieve
        detailed track information.
        """
        params = {"time": int(time.timestamp()) if time is not None else 0, "icao24": icao24}
        if json := self._get_json("/tracks/all", params=params):
            df = pd.DataFrame((dict(zip(self.TRACK_COLUMNS, x)) for x in json["path"]))
            df = df.assign(icao24=json["icao24"], callsign=json["callsign"])
            df = self._format_dataframe(df)
            df = self._format_history(df)
            return df
        return None

    def get_aircraft(
            self,
            icao24: str,
            begin: Optional[datetime] = None,
            end: Optional[datetime] = None,
    ) -> Optional[pd.DataFrame]:
        """Returns a flight table associated to an aircraft.

        Official documentation
        ----------------------
        This API call retrieves flights for a particular aircraft within a
        certain time interval. Resulting flights departed and arrived within
        [begin, end]. If no flights are found for the given period, HTTP stats
        404 - Not found is returned with an empty response body.
        """
        params = {
            "icao24": icao24,
            "begin": int(begin.timestamp()) if begin is not None else datetime.utcnow() - timedelta(days=1),
            "end": int(end.timestamp()) if end is not None else datetime.utcnow()
        }
        if json := self._get_json("/tracks/all", params=params):
            df = pd.DataFrame((dict(zip(self.AIRCRAFT_COLUMNS, x)) for x in json))
            return df.assign(
                firstSeen=lambda df: pd.to_datetime(df.firstSeen * 1e9).dt.tz_localize("utc"),
                lastSeen=lambda df: pd.to_datetime(df.lastSeen * 1e9).dt.tz_localize("utc"),
            ).sort_values("last_seen")
        return None

    def get_global_coverage(self) -> Optional[Sequence[Tuple[int, int, int]]]:
        if json := self._get_json("/range/coverage"):
            return json
        return None

    def get_arrival(
            self,
            icao: str,
            begin: Optional[datetime] = None,
            end: Optional[datetime] = None,
    ) -> Optional[pd.DataFrame]:
        """Returns a flight table associated to an airport.
        By default, returns the current table. Otherwise, you may enter a
        specific date (as a string, as an epoch or as a datetime)

        Official documentation
        ----------------------
        Retrieve flights for a certain airport which arrived within a given time
        interval [begin, end]. If no flights are found for the given period,
        HTTP stats 404 - Not found is returned with an empty response body.
        """
        params = {
            "icao": icao,
            "begin": int(begin.timestamp()) if begin is not None else datetime.utcnow() - timedelta(days=1),
            "end": int(end.timestamp()) if end is not None else datetime.utcnow()
        }
        if json := self._get_json("/flights/arrival", params=params):
            df = pd.DataFrame((dict(zip(self.AIRCRAFT_COLUMNS, x)) for x in json)).query("callsign == callsign")
            return df.assign(
                firstSeen=lambda df: pd.to_datetime(df.firstSeen * 1e9).dt.tz_localize("utc"),
                lastSeen=lambda df: pd.to_datetime(df.lastSeen * 1e9).dt.tz_localize("utc"),
                callsign=lambda df: df.callsign.str.strip()
            ).sort_values("lastSeen")
        return None

    def get_departure(
            self,
            icao: str,
            begin: Optional[datetime] = None,
            end: Optional[datetime] = None,
    ) -> Optional[pd.DataFrame]:
        """Returns a flight table associated to an airport.
        By default, returns the current table. Otherwise, you may enter a
        specific date (as a string, as an epoch or as a datetime)

        Official documentation
        ----------------------
        Retrieve flights for a certain airport which departed within a given
        time interval [begin, end]. If no flights are found for the given
        period, HTTP stats 404 - Not found is returned with an empty response
        body.
        """
        params = {
            "icao": icao,
            "begin": int(begin.timestamp()) if begin is not None else datetime.utcnow() - timedelta(days=1),
            "end": int(end.timestamp()) if end is not None else datetime.utcnow()
        }
        if json := self._get_json("/flights/departure", params=params):
            df = pd.DataFrame((dict(zip(self.AIRCRAFT_COLUMNS, x)) for x in json)).query("callsign == callsign")
            return df.assign(
                firstSeen=lambda df: pd.to_datetime(df.firstSeen * 1e9).dt.tz_localize("utc"),
                lastSeen=lambda df: pd.to_datetime(df.lastSeen * 1e9).dt.tz_localize("utc"),
                callsign=lambda df: df.callsign.str.strip()
            ).sort_values("lastSeen")
        return None

    @staticmethod
    def _check_lat(lat):
        if lat < -90 or lat > 90:
            raise ValueError("Invalid latitude {:f}! Must be in [-90, 90]".format(lat))

    @staticmethod
    def _check_lon(lon):
        if lon < -180 or lon > 180:
            raise ValueError("Invalid longitude {:f}! Must be in [-180, 180]".format(lon))

    @staticmethod
    def _format_dataframe(
            df: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        This function converts types, strips spaces after callsigns and sorts
        the DataFrame by timestamp.
        For some reason, all data arriving from OpenSky are converted to
        units in metric system. Optionally, you may convert the units back to
        nautical miles, feet and feet/min.
        """

        if "callsign" in df.columns and df.callsign.dtype == object:
            df.callsign = df.callsign.str.strip()

        df.icao24 = (
            df.icao24.apply(int, base=16)
                .apply(hex)
                .str.slice(2)
                .str.pad(6, fillchar="0")
        )

        if "squawk" in df.columns:
            df.squawk = (
                df.squawk.astype(str)
                    .str.split(".")
                    .str[0]
                    .replace({"nan": None})
            )

        time_dict: Dict[str, pd.Series] = dict()
        for colname in [
            "lastposupdate",
            "lastposition",
            "firstseen",
            "lastseen",
            "mintime",
            "maxtime",
            "time",
            "timestamp",
            "day",
            "hour",
        ]:
            if colname in df.columns:
                time_dict[colname] = pd.to_datetime(df[colname] * 1e9).dt.tz_localize("utc")

        return df.assign(**time_dict)

    @staticmethod
    def _format_history(
            df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        This function can be used in tandem with `_format_dataframe()` to
        convert (historical data specific) column types and optionally convert
        the units back to nautical miles, feet and feet/min.
        """
        # restore all types
        for column_name in [
            "lat",
            "lon",
            "velocity",
            "heading",
            "vertrate",
            "baroaltitude",
            "geoaltitude"
        ]:
            if column_name in df.columns:
                df[column_name] = df[column_name].astype(float)

        if "on_ground" in df.columns and df.onground.dtype != bool:
            df.onground = df.onground == "true"
            df.alert = df.alert == "true"
            df.spi = df.spi == "true"

        return df

    @staticmethod
    def _parse_instance(instance: Sequence[Any], fields: Mapping[str, Callable]):
        return {name: func(value) for value, (name, func) in zip(instance, fields.items()) if func}
