import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple, Sequence, Any, Mapping

import aiohttp
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
        "time_position": lambda x: datetime.fromtimestamp(x) if x is not None
            else datetime.now() - timedelta(seconds=15),
        "last_contact": None,
        "longitude": lambda x: float(x) if x else None,
        "latitude": lambda x: float(x) if x else None,
        "baro_altitude": lambda x: float(x) if x else 0,
        "on_ground": None,
        "velocity": lambda x: float(x) if x else 0,
        "azimuth": lambda x: float(x) if x else None,
        "vertical_rate": None,
        "sensors": None,
        "geo_altitude": None,
        "squawk": None,
        "spi": None,
        "position_source": None,
        "_": None
    }
    AIRCRAFT_COLUMNS = {
        "icao24": ("icao24", str),
        "callsign": ("callsign", lambda x: str(x).strip()),
        "firstSeen": ("first_seen", lambda x: datetime.fromtimestamp(x)),
        "lastSeen": ("last_seen", lambda x: datetime.fromtimestamp(x)),
        "estDepartureAirport": ("departure_airport", str),
        "estArrivalAirport": ("arrival_airport", str)
    }

    def __init__(
            self,
            username: Optional[str] = None,
            password: Optional[str] = None
    ) -> None:
        self._auth = (username, password) if username is not None else ()
        self._session = requests.Session()

    def _get_json(self, url_suffix: str, params: Mapping[str, str] = None):
        try:
            response = requests.get(f"{self.BASE_URL}{url_suffix}", auth=self._auth, params=params, timeout=15)
            if response.status_code == 200:
                return response.json()
            else:
                LOGGER.debug(f"Response not OK. Status {response.status_code} - {response.reason}")
        except Exception as error:
            LOGGER.debug(f"Request failed: {str(error)}")
        return None

    async def _get_json_async(self, url_suffix: str, params: Mapping[str, str] = None):
        async with aiohttp.ClientSession() as session:
            try:
                response = await session.get(f"{self.BASE_URL}{url_suffix}", params=params, timeout=15)
                if response.status == 200:
                    return await response.json()
                else:
                    LOGGER.debug(f"Response not OK. Status {response.status} - {response.reason}")
            except Exception as error:
                LOGGER.debug(f"Request failed: {str(error)}")
        return None

    async def get_airplanes(
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
        params = {"time": int(time.timestamp()) if time is not None else 0, "icao24": icao24 or ''}

        if bounds:
            if len(bounds) != 4:
                raise ValueError("Invalid bounding box! Must be "
                                 "[min_latitude, max_latitude, min_longitude, max_latitude]")
            self._check_lat(bounds[0])
            self._check_lat(bounds[1])
            self._check_lon(bounds[2])
            self._check_lon(bounds[3])
            params.update({"lamin": bounds[0], "lamax": bounds[1], "lomin": bounds[2], "lomax": bounds[3]})

        if json := await self._get_json_async("/states/all", params=params):
            data = [self._parse_state(x) for x in json["states"]]
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
        beneficial to retrieve a list of flights with the API methods from
        above, and use these results with the given time stamps to retrieve
        detailed track information.
        """
        raise NotImplementedError

    def get_flights(
            self,
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
        if end - begin > timedelta(hours=2):
            raise ValueError("An interval of more than 2 hours not allowed")
        params = {
            "begin": str(int((begin or datetime(*datetime.utcnow().timetuple()[:3]) - timedelta(days=1)).timestamp())),
            "end": str(int((end or datetime(*datetime.utcnow().timetuple()[:3])).timestamp()))
        }
        if json := self._get_json("/flights/all", params=params):
            data = sorted((self._parse_aircraft(x) for x in json), key=lambda x: x["last_seen"])
            return pd.DataFrame(data).set_index('icao24')
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
            "begin": int((begin or datetime(*datetime.utcnow().timetuple()[:3]) - timedelta(days=1)).timestamp()),
            "end": int((end or datetime(*datetime.utcnow().timetuple()[:3])).timestamp())
        }
        if json := self._get_json("/flights/aircraft", params=params):
            data = sorted((self._parse_aircraft(x) for x in json), key=lambda x: x["last_seen"])
            return pd.DataFrame(data).set_index('icao24')
        return None

    def get_global_coverage(self) -> Optional[Sequence[Tuple[int, int, int]]]:
        if json := self._get_json("/range/coverage"):
            return json
        return None

    def get_arrival(
            self,
            airport: str,
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
            "airport": airport,
            "begin": int((begin or datetime.utcnow() - timedelta(days=2)).timestamp()),
            "end": int((end or datetime.utcnow()).timestamp())
        }
        if json := self._get_json("/flights/arrival", params=params):
            data = sorted((self._parse_aircraft(x) for x in json), key=lambda x: x["last_seen"])
            return pd.DataFrame(data).set_index('icao24')
        return None

    def get_departure(
            self,
            airport: str,
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
            "airport": airport,
            "begin": int((begin or datetime.utcnow() - timedelta(days=1)).timestamp()),
            "end": int((end or datetime.utcnow()).timestamp())
        }
        if json := self._get_json("/flights/departure", params=params):
            data = sorted((self._parse_aircraft(x) for x in json), key=lambda x: x["last_seen"])
            return pd.DataFrame(data).set_index('icao24')
        return None

    @staticmethod
    def _check_lat(lat):
        if lat < -90 or lat > 90:
            raise ValueError("Invalid latitude {:f}! Must be in [-90, 90]".format(lat))

    @staticmethod
    def _check_lon(lon):
        if lon < -180 or lon > 180:
            raise ValueError("Invalid longitude {:f}! Must be in [-180, 180]".format(lon))

    def _parse_state(self, state: Sequence[Any]):
        return {name: func(value) for value, (name, func) in zip(state, self.STATE_COLUMNS.items()) if func}

    def _parse_aircraft(self, aircraft: Mapping[str, Any]):
        return {self.AIRCRAFT_COLUMNS[key][0]: self.AIRCRAFT_COLUMNS[key][1](value)
                for key, value in aircraft.items() if key in self.AIRCRAFT_COLUMNS}
