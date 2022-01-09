import pandas as pd


def get_airlines() -> pd.DataFrame:
    columns = ["id", "name", "alias", "iata", "icao", "callsign", "country", "active"]

    airlines = pd.read_csv(
        "https://raw.githubusercontent.com/jpatokal/openflights/master/data/airlines.dat",
        names=columns,
        header=None,
        index_col=["icao"],
        usecols=["icao", "name", "active"],
        keep_default_na=False
    ).replace("\\N", '')

    airlines = airlines[(airlines.active == "Y") &
                        ~airlines.index.duplicated(keep='first') &
                        airlines.index.str.match(r"\w{3}")]
    return airlines.drop(columns=["active"])
