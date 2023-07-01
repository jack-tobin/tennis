"""Automated tennis court bookings in Python."""

from __future__ import annotations

import datetime as dt
import sys
from argparse import ArgumentParser
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

import requests as re
from auth import TennisAuth
from responses import ResponseProcessor, ResponseStatus

from tennis import StrEnum, log


@dataclass
class BookingSlot:
    """Booking slot struct."""

    court_number: int
    date: dt.date
    start_time: dt.time
    end_time: dt.time
    is_open: bool
    cost: float

    @property
    def duration(self) -> float:
        """Return hours between start and end time."""
        start_datetime = dt.datetime.combine(self.date, self.start_time)
        end_datetime = dt.datetime.combine(self.date, self.end_time)
        return (end_datetime - start_datetime).seconds // 3600

    @property
    def is_double_slot(self) -> bool:
        """Return whether the slot is available for a double booking."""
        two_hours = 2.0
        return self.duration >= two_hours

    @property
    def is_free(self) -> bool:
        """Return whether the slot is free, e.g. cost is zero."""
        return self.cost == 0


class CourtLocation(StrEnum):
    """Enum of string court locations."""

    LYLE = 'lyle'
    STRATFORD = 'stratford'


@dataclass
class BookingConfirmation:
    """Booking confirmation struct."""

    booking_date: dt.date
    booking_time: dt.time
    length_in_hours: int
    location: CourtLocation


@dataclass
class TennisScheduler:
    """Scheduler for tennis court bookings."""

    booking_date: dt.date
    target_time: dt.time
    location: CourtLocation = field(default=CourtLocation.LYLE)
    include_paid_slots: bool = field(default=False)

    auth: TennisAuth = field(init=False)
    response: ResponseProcessor = field(init=False)
    success: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        # validate reservation date.
        if self.booking_date > self.max_booking_date:
            raise RuntimeError('Unable to book further than 14 days in advance.')

        self._authenticate()

    @property
    def max_booking_date(self) -> dt.date:
        """Max available booking date."""
        return dt.datetime.now(tz=dt.timezone.utc).date() + dt.timedelta(days=14)

    def _authenticate(self) -> None:
        self.auth = TennisAuth(role_id=...)

    def _get_response_data(self) -> dict[str, Any]:
        """Get response data after validating response is successful."""
        response = ResponseProcessor(re.get(self.url, timeout=60))
        match response.status:
            case ResponseStatus.Ok:
                self.response = response
                return self.response.data
            case _:
                raise RuntimeError(f'{self.response}')

    def _get_slots(self) -> Iterator[BookingSlot]:
        """Get list of all booking slots on date."""
        response_data = self._get_response_data()
        for court in response_data['Resources']:
            for day in court['Days']:
                for session in day['Sessions']:
                    try:
                        court_number = court['Number'] + 1
                        session_date = dt.datetime.strptime(
                            day['Date'], '%Y-%m-%dT%H:%M:%S').replace(tzinfo=dt.timezone.utc).date()
                        session_start = dt.time(int(session['StartTime'] / 60), 0)
                        session_end = dt.time(int(session['EndTime'] / 60), 0)
                        session_is_open = session['Capacity'] != 0
                        session_cost = session['MemberPrice']
                    except Exception:
                        log.exception('Exception when parsing session')
                        continue

                    yield BookingSlot(
                        court_number,
                        session_date,
                        session_start,
                        session_end,
                        session_is_open,
                        session_cost,
                    )

    @property
    def url(self) -> str:
        """Return url to request the list of booking slots."""
        return f'https://{self.location}.newhamparkstennis.org.uk/v0/VenueBooking/{self.location}_newhamparkstennis_org_uk/GetVenueSessions?resourceID=&startDate={self.booking_date}&endDate={self.booking_date}&roleId=&_={self.auth.role_id}'  # noqa: E501

    @property
    def target_time_stamp(self) -> int:
        """Return target booking time stmap.

        Times returned by API are listed in minutes from midnight.

        """
        return self.target_time.hour * 60

    def attempt_booking(self) -> None | BookingConfirmation:
        """Attempt to book reservation."""
        available_slots = [
            slot for slot in self._get_slots()
            if slot.is_open
        ]

        # Skip paid slots.
        if not self.include_paid_slots:
            available_slots = [
                slot for slot in available_slots if slot.is_free
            ]

        if available_slots:
            log.info(f'Found {len(available_slots)} available slots.')
        else:
            raise RuntimeError(f'No slots found on date {self.booking_date}')

        # Rank slots
        # First rank by capacity
        # Then rank by proximity to start time
        all_slots = ...

        return


@dataclass
class Args:
    """Command line args struct."""

    booking_date: dt.date
    target_time: dt.time
    location: CourtLocation
    include_paid_slots: bool


def parse_args(argv: list[str]) -> Args:
    """Parse command line arguments."""
    parser = ArgumentParser()
    parser.add_argument(
        '--booking_date',
        action='store',
        dest='booking_date',
        type=lambda x: dt.datetime.strptime(x, '%Y-%m-%d').replace(tzinfo=dt.timezone.utc).date(),
        default=dt.datetime.now(tz=dt.timezone.utc).date() + dt.timedelta(days=14),
        required=False,
        help='Date to request booking for.',
    )
    parser.add_argument(
        '--target_time',
        action='store',
        dest='target_time',
        type=lambda x: dt.time.fromisoformat(x),
        default=dt.time.fromisoformat('10:00'),
        required=False,
        help='Time in UTC to request booking for. Must be in format HH:MM',
    )
    parser.add_argument(
        '--location',
        action='store',
        dest='location',
        type=lambda x: CourtLocation.get(x),
        default=CourtLocation.LYLE,
        required=False,
        help=('Tennis court location to request. Currently available options are:'
              '["lyle", "stratford"]'),
    )
    parser.add_argument(
        '--include_paid_slots',
        action='store_true',
        dest='include_paid_slots',
        default=False,
        required=False,
        help='Whether to search for paid booking slots.',
    )
    return Args(**vars(parser.parse_args(argv)))


def main() -> int:
    """Run tennis scheduler process."""
    log.info('Initialising tennis reservation bot.')

    args = parse_args(sys.argv[1:])
    log.info(f'Input arguments: {args}')

    scheduler = TennisScheduler(
        booking_date=args.booking_date,
        target_time=args.target_time,
        location=args.location,
        include_paid_slots=args.include_paid_slots,
    )
    try:
        scheduler.attempt_booking()
    except Exception:
        log.exception('Error in scheduler')
        return -1

    if not scheduler.success:
        log.info(f'Unable to complete booking request: {scheduler.response}')
        return -1

    log.info('Scheduler exited successfully.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
