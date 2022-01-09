import pandas as pd


def get_airports() -> pd.DataFrame:
    columns = ["id", "name", "city", "country", "iata", "icao", "latitude", "longitude", "altitude",
               "timezone", "daylight_savings_time", "timezone_db", "type", "source"]
    use_columns = ["name", "city", "country", "icao", "latitude", "longitude", "altitude"]

    airports = pd.read_csv(
        "https://raw.githubusercontent.com/jpatokal/openflights/master/data/airports.dat",
        names=columns, header=None, index_col=["icao"], usecols=use_columns
    )
    return airports.replace("\\N", '').dropna().astype({"latitude": float, "longitude": float, "altitude": int})
