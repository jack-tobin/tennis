"""Response helpers."""

from __future__ import annotations

from dataclasses import dataclass
from json import loads
from typing import Any

from requests import Response

from tennis import StrEnum


class ResponseStatus(StrEnum):
    """Response status enumeration class."""

    Ok = 'OK'
    BadRequest = 'Bad Request'
    InternalServerError = 'Internal Server Error'

    def __bool__(self) -> bool:
        """Return True if the response is 200: OK."""
        return self == self.Ok

    @classmethod
    def from_status_code(cls, status_code: int) -> ResponseStatus:
        """Return a response status instance from a status code.

        Returns
        -------
        ResponseStatus
            Ok if 200, BadRequest if 400, InternalServerError if 500.

        """
        match status_code // 100:
            case 2:
                return cls.Ok
            case 4:
                return cls.BadRequest
            case 5:
                return cls.InternalServerError
            case _:
                raise ValueError(f'Unknown status code: {status_code}')


@dataclass
class ResponseProcessor:
    """Processor for API responses.

    Parameters
    ----------
    response : Response
        A python requests library response object.

    """

    response: Response

    @property
    def data(self) -> dict[str, Any]:
        """Return json-decoded response text data.

        Returns
        -------
        dict[str, Any]
            JSON-decoded response text data.

        """
        return loads(self.response.text)

    @property
    def status(self) -> ResponseStatus:
        """Return status enumeration of response.

        Returns
        -------
        ResponseStatus
            Response status Enum instance based on response status code.

        """
        return ResponseStatus.from_status_code(self.response.status_code)

    def __str__(self) -> str:
        """Return string representation of response."""
        return f'Response[{self.response.status_code}: {self.status}]'

    def __bool__(self) -> bool:
        """Return whether response status code is in the 200s."""
        return self.status == ResponseStatus.Ok
