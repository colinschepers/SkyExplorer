import pandas as pd


def _get_open_flights_airports():
    columns = ["id", "name", "city", "country", "iata", "icao", "latitude", "longitude", "altitude",
               "timezone", "daylight_savings_time", "timezone_db", "type", "source"]

    airports = pd.read_csv(
        "https://raw.githubusercontent.com/jpatokal/openflights/master/data/airports.dat",
        names=columns, header=None, index_col=["id"], usecols=columns[:9]
    )

    return airports.replace("\\N", '').astype({"altitude": int})


def _get_our_airports_airports():
    columns = {"ident": "icao", "type": "type", "name": "name", "iso_country": "country",
               "latitude_deg": "latitude", "longitude_deg": "longitude", "elevation_ft": "altitude"}

    airports = pd.read_csv(
        "https://davidmegginson.github.io/ourairports-data/airports.csv",
        index_col=["ident"], usecols=list(columns) + ["scheduled_service"]
    ).rename(columns=columns)

    countries = pd.read_csv(
        "https://davidmegginson.github.io/ourairports-data/countries.csv",
        index_col=["code"], usecols=["code", "name"]
    )

    airports = airports[airports.scheduled_service == "yes"].drop(columns=["scheduled_service"])
    airports["country"] = airports["country"].apply(lambda code: countries.loc[code]["name"])

    return airports.dropna().astype({"altitude": int})


def get_airports():
    return _get_open_flights_airports()
