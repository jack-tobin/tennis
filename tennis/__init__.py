"""Tennis court booking bot."""

import logging
from enum import Enum
from pathlib import Path

import yaml


class StrEnum(str, Enum):
    """String enum class.

    String enums are helpful because they standardise a set of string values
    and also because the instances of the Enum are also strings, enabling
    any string methods to apply here too.

    """

    @classmethod
    def get(cls, value: str) -> str:
        """Get the enum that matches a string value."""
        for val in cls:
            if val == value:
                return val
        raise RuntimeError(f'No match for "{value}" in enum {cls.__name__}')


# specify logging level as info
logging.basicConfig(level=logging.INFO)
log = logging.getLogger()

# Configuration.
with Path('conf.yml').open() as f:
    config = yaml.safe_load(f)
