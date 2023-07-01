"""Tennis court booking bot."""

import logging
from enum import Enum


class StrEnum(str, Enum):
    """String enum class."""

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
