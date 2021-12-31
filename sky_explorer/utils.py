import pycountry


def get_country_name(alpha_2: str) -> str:
    if country := pycountry.countries.get(alpha_2=alpha_2):
        return country.name
    return alpha_2
