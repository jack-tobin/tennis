"""Automated tennis court bookings in Python."""

# ruff: noqa: DTZ011, DTZ007, DTZ005

from __future__ import annotations

import datetime as dt
import sys
import time
from argparse import ArgumentParser, Namespace
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

import requests as re
from payments import Card, Payment, PaymentResult
from responses import ResponseProcessor, ResponseStatus

from tennis import StrEnum, config, log

LOCAL_TIME_BOOKINGS_OPEN = dt.time(9, 00, tzinfo=None)


class CourtLocation(StrEnum):
    """Enum of string court locations."""

    LYLE = 'lyle'
    STRATFORD = 'stratford'


@dataclass
class BookingConfirmation:
    """Booking confirmation struct."""

    location: CourtLocation
    court_number: int
    booking_date: dt.date
    booking_time: dt.time
    length_in_hours: int


@dataclass
class BookingSlot:
    """Booking slot struct."""

    location: CourtLocation
    court_number: int
    date: dt.date
    start_time: dt.time
    end_time: dt.time
    is_open: bool
    cost: float
    lighting_cost: float

    @property
    def duration(self) -> float:
        """Return hours between start and end time.

        Returns
        -------
        float
            Total continuous duration of the booking in hours.

        """
        start_datetime = dt.datetime.combine(self.date, self.start_time)
        end_datetime = dt.datetime.combine(self.date, self.end_time)
        return (end_datetime - start_datetime).seconds // 3600

    @property
    def is_double_slot(self) -> bool:
        """Return whether the slot is available for a double booking.

        Returns
        -------
        bool
            Whether the duration of the booking slot in hours is at least 2.

        """
        two_hours = 2.0
        return self.duration >= two_hours

    @property
    def is_paid_lighting(self) -> bool:
        """Return whether the slot is a paid lighting slot which cost more.

        Returns
        -------
        bool
            True if lighting cost is nonzero, False otherwise.

        """
        return self.lighting_cost == 0

    def distance_from_target_time(self, target_time: dt.time) -> float:
        """Compute the distance in hours from the target time.

        Parameters
        ----------
        target_time : dt.time
            Target start time.

        Returns
        -------
        float
            Returns the absolute distance of a given booking slot's start time
            from the target start time.

        """
        start_datetime = dt.datetime.combine(self.date, self.start_time)
        target_datetime = dt.datetime.combine(self.date, target_time)
        return round(abs((start_datetime - target_datetime).total_seconds() / 3600), 2)

    def is_available_for_times(self, start_time: dt.time, end_time: dt.time) -> bool:
        """Determine whether the slot is available for a given set of start and end times.

        Parameters
        ----------
        start_time : dt.time
            Requested start time.
        end_time : dt.time
            Requested end time.

        Returns
        -------
        bool
            Whether the slot is available between the given start and end times.

        """
        return start_time >= self.start_time and end_time <= self.end_time

    def request(self, start_time: dt.time, end_time: dt.time, card: Card) -> BookingConfirmation:
        """Request booking for this slot with a card.

        Parameters
        ----------
        start_time : dt.time
            Requested start time.
        end_time : dt.time
            Requested end time.
        card : Card
            Credit card struct to use for 'payment'.

        Returns
        -------
        BookingConfirmation
            A confirmed booking.

        Raises
        ------
        RuntimeError
            If slot is unavailable, raise an error.
        RuntimeError
            If the payment status is not "ok", raise an error.

        """
        if not self.is_available_for_times(start_time, end_time):
            raise RuntimeError('Booking not available for requested times.')

        # Post payment.
        if self.cost:
            match Payment(amount=self.cost, card=card).authorize():
                case PaymentResult.Ok:
                    pass
                case _:
                    raise RuntimeError('Error in payment')

        return BookingConfirmation(
            location=self.location,
            court_number=self.court_number,
            booking_date=self.date,
            booking_time=self.start_time,
            length_in_hours=min(2, int(self.duration)),
        )


@dataclass
class TennisScheduler:
    """Scheduler for tennis court bookings."""

    booking_date: dt.date
    target_start_time: dt.time
    target_end_time: dt.time
    location: CourtLocation = field(default=CourtLocation.LYLE)
    include_paid_lighting_slots: bool = field(default=False)
    exclude_one_hour_slots: bool = field(default=True)
    card: Card = field(init=False)

    response: ResponseProcessor = field(init=False)
    success: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        """Post init operations.

        Raises
        ------
        RuntimeError
            If the booking date is more than 2 weeks from now, raise an error.

        """
        if self.booking_date > self.max_booking_date:
            raise RuntimeError('Unable to book further than 14 days in advance.')

        self.card = Card(
            number=config['card']['number'],
            name=config['card']['name'],
            cvv=config['card']['cvv'],
            exp_month=config['card']['exp_month'],
            exp_year=config['card']['exp_year'],
        )

    @property
    def current_datetime(self) -> dt.datetime:
        """Return current datetime.

        Returns
        -------
        dt.datetime
            The current date-time.

        """
        return dt.datetime.now()

    @property
    def max_booking_date(self) -> dt.date:
        """Max available booking date.

        Returns
        -------
        dt.date
            The maximum available date we can book today.

        """
        return self.current_datetime.date() + dt.timedelta(days=14)

    def _get_response_data(self) -> dict[str, Any]:
        """Get response data after validating response is successful.

        Returns
        -------
        dict[str, Any]
            JSON-decoded API response data containing information about bookings.

        """
        response = ResponseProcessor(re.get(self.url, timeout=60))
        match response.status:
            case ResponseStatus.Ok:
                self.response = response
                return self.response.data
            case _:
                raise RuntimeError(f'{self.response}')

    def _get_slots(self) -> Iterator[BookingSlot]:
        """Get list of all booking slots on date.

        Yields
        ------
        BookingSlot
            This iteratively yields booking slots that are available for booking.

        """
        response_data = self._get_response_data()
        for court in response_data['Resources']:
            for day in court['Days']:
                for session in day['Sessions']:
                    try:
                        court_number = court['Number'] + 1
                        session_date = (
                            dt.datetime.strptime(day['Date'], '%Y-%m-%dT%H:%M:%S')
                            .date()
                        )
                        session_start = dt.time(int(session['StartTime'] / 60), 0)
                        session_end = dt.time(int(session['EndTime'] / 60), 0)
                        session_is_open = session['Capacity'] != 0
                        session_cost = session['MemberPrice']
                        session_lighting_cost = session['LightingCost']
                    except Exception:
                        log.exception('Exception when parsing session')
                        continue

                    yield BookingSlot(
                        location=self.location,
                        court_number=court_number,
                        date=session_date,
                        start_time=session_start,
                        end_time=session_end,
                        is_open=session_is_open,
                        cost=session_cost,
                        lighting_cost=session_lighting_cost,
                    )

    @property
    def url(self) -> str:
        """Return url to request the list of booking slots.

        Returns
        -------
        str
            Returns a string URL for the bookings slot GET request.

        """
        return (
            f'https://{self.location}.newhamparkstennis.org.uk/v0/VenueBooking/'
            f'{self.location}_newhamparkstennis_org_uk/'
            f'GetVenueSessions?resourceID=&'
            f'startDate={self.booking_date}&'
            f'endDate={self.booking_date}&'
            f'roleId=&_={config["user"]["role_id"]}'
        )

    @property
    def target_start_time_stamp(self) -> int:
        """Return target booking time stmap.

        Times returned by API are listed in minutes from midnight.

        Returns
        -------
        int
            The target start time coded as a timestamp of minutes from midnight.

        """
        return self.target_start_time.hour * 60

    def _wait_for_opening_time(self) -> None:
        """Wait for scheduled booking opening time."""
        seconds_to_sleep = 0.50
        minimum_date_bookings_are_possible = self.booking_date - dt.timedelta(days=14)
        booking_open_datetime = dt.datetime.combine(
            minimum_date_bookings_are_possible,
            LOCAL_TIME_BOOKINGS_OPEN,
        )
        while self.current_datetime < booking_open_datetime:
            log.info(f'Bookings not yet open, sleeping for {seconds_to_sleep} seconds...')
            time.sleep(seconds_to_sleep)

    def _filter_slots(self, slots: list[BookingSlot]) -> list[BookingSlot]:
        """Filter slots per user-defined boolean filters.

        Parameters
        ----------
        slots : list[BookingSlot]
            List of all open booking slots.

        Returns
        -------
        list[BookingSlot]
            List of filtered booking slots.

        """
        filtered_slots = slots.copy()
        # Exclude slots if the have paid lighting.
        if not self.include_paid_lighting_slots:
            filtered_slots = [
                slot for slot in slots if slot.is_paid_lighting
            ]

        # Exclude one hour slots.
        if self.exclude_one_hour_slots:
            filtered_slots = [
                slot for slot in filtered_slots if slot.is_double_slot
            ]

        return filtered_slots

    def _collect_slots(self) -> list[BookingSlot]:
        """Collect all available slots on the booking date.

        Returns
        -------
        list[BookingSlot]
            List of booking slots available for booking.

        Raises
        ------
        RuntimeError
            If no slots are available on the given date, an error is raised.

        """
        open_slots = [
            slot for slot in self._get_slots()
            if slot.is_open
        ]

        filtered_slots = self._filter_slots(open_slots)

        # If there are any left, return them
        if not filtered_slots:
            raise RuntimeError(f'No available slots found on date {self.booking_date}')

        log.info(f'Found {len(filtered_slots)} available slots.')
        return filtered_slots

    def _rank_slots(self, slots: list[BookingSlot]) -> list[BookingSlot]:
        """Rank the slots by their optimalness.

        First rank by proximity to target start time, then rank by total capacity.

        Parameters
        ----------
        slots : list[BookingSlot]
            List of filtered booking slots.

        Returns
        -------
        list[BookingSlot]
            List of slots ranked by their optimalness, most optimal being first.

        """
        slots_ranked_by_proximity = sorted(
            slots,
            key=lambda x: x.distance_from_target_time(self.target_start_time),
        )
        return sorted(
            slots_ranked_by_proximity,
            key=lambda x: x.duration,
            reverse=True,
        )

    def request_booking(self, slot: BookingSlot) -> BookingConfirmation | None:
        """Request a booking within a given slot.

        Parameters
        ----------
        slot : BookingSlot
            A slot to attempt to book with target start and end times.


        Returns
        -------
        BookingConfirmation | None
            Either None if the booking slot is unable to be requested, or
            a confirmed booking if it is.

        """
        try:
            return slot.request(self.target_start_time, self.target_end_time, self.card)
        except Exception:
            log.exception(f'Unable to confirm booking for slot {slot}')
            return None

    def book(self) -> BookingConfirmation:
        """Attempt to book reservation.

        Returns
        -------
        BookingConfirmation
            Booking confirmation.

        Raises
        ------
        RuntimeError
            If there is an unknown issue with the booking and the confirmation
            is None, then raise an error.

        """
        self._wait_for_opening_time()
        slots = self._collect_slots()
        ranked_slots = self._rank_slots(slots)

        # Recursively attempt to book until success.
        while (confirmation := self.request_booking(ranked_slots[0])) is None:
            attempted_slot = ranked_slots.pop(0)
            log.info(f'Could not successfully book slot {attempted_slot}, attempting next.')
            if not ranked_slots:
                break

        if confirmation is None:
            raise RuntimeError('Error in booking request.')

        return confirmation


@dataclass
class Args:
    """Command line args struct.

    This allows for static type checking and intellisense for argparse command line
    arguments.

    """

    booking_date: dt.date
    target_start_time: dt.time
    target_end_time: dt.time
    location: CourtLocation
    include_paid_lighting_slots: bool = field(default=False)
    exclude_one_hour_slots: bool = field(default=True)

    @classmethod
    def from_namespace(cls, namespace: Namespace) -> Args:
        """Return instance of Args from an Argparse namespace instance.

        Parameters
        ----------
        namespace : Namespace
            An argparse Namespace.

        Returns
        -------
        Args
            Instance of class Args.

        """
        return cls(**vars(namespace))


def parse_args(argv: list[str]) -> Args:
    """Parse command line arguments.

    Parameters
    ----------
    argv : list[str]
        Command line argument vector as a list, with the first element (script
        name) already excluded.

    Returns
    -------
    Args
        Instance of args struct.

    """
    parser = ArgumentParser()
    parser.add_argument(
        '--location',
        action='store',
        dest='location',
        type=CourtLocation.get,
        default=CourtLocation.LYLE,
        required=False,
        help=('Tennis court location to request. Currently available options are:'
              '["lyle", "stratford"]'),
    )
    parser.add_argument(
        '--booking_date',
        action='store',
        dest='booking_date',
        type=lambda x: dt.datetime.strptime(x, '%Y-%m-%d').date(),
        default=dt.date.today() + dt.timedelta(days=14),
        required=False,
        help='Date to request booking for.',
    )
    parser.add_argument(
        '--target_start_time',
        action='store',
        dest='target_start_time',
        type=dt.time.fromisoformat,
        default=dt.time(10, 00),
        required=False,
        help='Time in UTC to request booking for. Must be in format HH:MM',
    )
    parser.add_argument(
        '--target_end_time',
        action='store',
        dest='target_end_time',
        type=dt.time.fromisoformat,
        default=dt.time(12, 00),
        required=False,
        help='End of booking to request. Must be in format HH:MM',
    )
    parser.add_argument(
        '--exclude_one_hour_slots',
        action='store_true',
        dest='exclude_one_hour_slots',
        default=True,
        required=False,
        help='Whether to exclude one hour only slots.',
    )
    parser.add_argument(
        '--include_paid_lighting_slots',
        action='store_true',
        dest='include_paid_lighting_slots',
        default=False,
        required=False,
        help='Whether to search for paid lit booking slots.',
    )
    return Args.from_namespace(parser.parse_args(argv))


def main() -> int:
    """Run tennis scheduler process."""
    log.info('Initialising tennis reservation bot.')

    args = parse_args(sys.argv[1:])
    log.info(f'Input arguments:\n{args}')

    scheduler = TennisScheduler(
        booking_date=args.booking_date,
        target_start_time=args.target_start_time,
        target_end_time=args.target_end_time,
        location=args.location,
        include_paid_lighting_slots=args.include_paid_lighting_slots,
        exclude_one_hour_slots=args.exclude_one_hour_slots,
    )
    try:
        confirmation = scheduler.book()
    except Exception:
        log.exception('Error in scheduler')
        return -1

    log.info(f'Booking confirmed:\n{confirmation}')

    log.info('Scheduler exited successfully.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
