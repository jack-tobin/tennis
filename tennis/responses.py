"""Response helpers."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from json import loads
from typing import Any

from requests import Response


class ResponseStatus(str, Enum):
    Ok = 'OK'
    BadRequest = 'Bad Request'
    InternalServerError = 'Internal Server Error'

    def __bool__(self) -> bool:
        return self == self.Ok

    @classmethod
    def from_status_code(cls, status_code: int) -> ResponseStatus:
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
    response: Response

    @property
    def data(self) -> dict[str, Any]:
        return loads(self.response.text)

    @property
    def status(self) -> ResponseStatus:
        return ResponseStatus.from_status_code(self.response.status_code)

    def __str__(self) -> str:
        return f'Response[{self.response.status_code}: {self.status}]'

    def __bool__(self) -> bool:
        return self.status == ResponseStatus.Ok
