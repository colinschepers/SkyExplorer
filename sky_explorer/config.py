from typing import Any

import yaml


def load_yaml(filename: str) -> Any:
    with open(filename, "r") as file:
        return yaml.safe_load(file)


CONFIG = load_yaml("config.yaml")
