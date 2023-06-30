"""Automated tennis court bookings in Python."""

from __future__ import annotations

import datetime as dt
import json
import logging
import sys
from argparse import ArgumentParser
from dataclasses import dataclass, field
from enum import Enum

import requests as re

# specify logging level as info
logging.basicConfig(level=logging.INFO)
log = logging.getLogger()


@dataclass
class Args:
    booking_date: dt.date
    target_time: dt.time
    location: CourtLocation


@dataclass
class BookingSlot:
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
        return self.duration >= 2.0


class StrEnum(str, Enum):
    """Generic string enumeration class."""

    @classmethod
    def get(cls, value: str) -> CourtLocation:
        """Get the enum that matches a string value."""
        try:
            return next(val for val in cls if val == value)
        except StopIteration:
            raise RuntimeError('No match for {value} in CourtLocation')


class CourtLocation(StrEnum):
    LYLE = 'lyle'
    STRATFORD = 'stratford'


def parse_args(argv: list[str]) -> Args:
    parser = ArgumentParser()
    parser.add_argument(
        '--booking_date',
        action='store',
        dest='booking_date',
        type=lambda x: dt.datetime.strptime(x, '%Y-%m-%d').date(),
        default=dt.date.today() + dt.timedelta(days=14),
        required=False,
        help='Date to request booking for.'
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
              '["lyle", "stratford"]')
    )
    return Args(**vars(parser.parse_args(argv)))


def main() -> int:
    log.info('Initialising tennis reservation bot.')

    args = parse_args(sys.argv[1:])
    log.info(f'Input arguments: {args}')

    scheduler = TennisScheduler(
        booking_date=args.booking_date,
        target_time=args.target_time,
        location=args.location,
    )
    scheduler.attempt_booking()

    if not scheduler.success:
        log.info(f'Unable to complete booking request: {scheduler.response}')
        return -1

    log.info(f'Booking not confirmed. Details: {scheduler.response}')
    return 1


@dataclass
class TennisScheduler:

    booking_date: dt.date = field(default=dt.date.today() + dt.timedelta(days=14))
    target_time: dt.time = field(default=dt.time(10, 0))
    location: CourtLocation = field(default=CourtLocation.LYLE)

    include_paid_slots: bool = field(default=False)

    success: bool = field(default=False, init=False)

    @property
    def response(self) -> str:
        return ''

    @property
    def target_time_stamp(self) -> int:
        """Return target booking time stmap.

        Times returned by API are listed in minutes from midnight.

        """
        return self.target_time.hour * 60

    def __post_init__(self) -> None:
        # validate reservation date.
        if self.booking_date > dt.date.today() + dt.timedelta(days=14):
            raise RuntimeError('Unable to book reservations greater than 14 days in advance.')

    def attempt_booking(self) -> int:
        """Attempt to book reservation."""

        # TODO: how to request authentication via LTA?

        # Construct URL.
        url = f'https://{self.location}.newhamparkstennis.org.uk/v0/VenueBooking/{self.location}_newhamparkstennis_org_uk/GetVenueSessions?resourceID=&startDate={self.booking_date}&endDate={self.booking_date}&roleId=&_=1688152712056'

        # Get API response.
        response = re.get(url)
        if response.status_code != 200:
            raise RuntimeError(f'Bad request: {response.text}')
        response_json = json.loads(response.text)

        # Collect all slots.
        all_slots: list[BookingSlot] = []
        for court in response_json['Resources']:
            for day in court['Days']:
                for session in day['Sessions']:
                    try:
                        slot = BookingSlot(
                            court_number=court['Number'] + 1,
                            date=dt.datetime.strptime(day['Date'], '%Y-%m-%dT%H:%M:%S').date(),
                            start_time=dt.time(int(session['StartTime'] / 60), 0),
                            end_time=dt.time(int(session['EndTime'] / 60), 0),
                            is_open=session['Capacity'] != 0,
                            cost=session['MemberPrice'],
                        )
                    except Exception:
                        log.exception('Exception when parsing session')
                        continue
                    all_slots.append(slot)

        # Filter out booked slots
        available_slots = [slot for slot in all_slots if slot.is_open]

        # Filter out slots with cost if we're avoiding those.
        if not self.include_paid_slots:
            available_slots = [slot for slot in available_slots if slot.cost == 0]

        if available_slots:
            log.info(f'Found {len(available_slots)} available slots.')
        else:
            log.info(f'No open slots on requested date {self.booking_date}. Exiting.')
            return -1


        # Rank slots
        # First rank by capacity
        # Then rank by proximity to start time
        all_slots = ...










        return 'hello'

if __name__ == '__main__':
    sys.exit(main())
