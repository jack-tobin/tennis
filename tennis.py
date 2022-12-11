#!/usr/bin/env python
# -*-coding:utf-8 -*-
"""
@File    :   tennis.py
@Time    :   2022/11/06 07:51:22
@Author  :   Jack Tobin
@Version :   1.0
@Contact :   tobjack330@gmail.com
"""


from abc import ABC, abstractmethod, abstractproperty
from selenium import webdriver
from bs4 import BeautifulSoup
import requests as re
import datetime as dt
import logging as log


# specify logging level as info
log.basicConfig(level = log.INFO)


def main() -> int:
    log.info('Initialising tennis reservation bot.')
    
    # target reservation date
    res_date = dt.date.today() + dt.timedelta(days=14)
    log.info(f'Set target reservation date of: {res_date}')

    # initialize webdriver
    scheduler = TennisScheduler(reservation_date=res_date, park_location='lyle')

    # attempt booking
    log.info(f'Attempting booking on {scheduler.reservation_date}')
    scheduler.attempt_booking()
    if scheduler.success:
        log.info(f'Success! Booking confirmed. Details: {scheduler.response}')
        return 0
    else:
        log.info(f'Booking not confirmed. Details: {scheduler.response}')
        return 1


class Scheduler(ABC):
    def __init__(self):
        self._browser = None
        self._url = None
        self._response = None

        # related to status of booking
        self.success = False

    @property
    def browser(self):
        """Retrieve web driver."""
        if not self._browser:
            self._browser = webdriver.Chrome(executable_path='~/chromedriver.exe')
        return self._browser

    @property
    def url(self):
        return self._url

    @url.setter
    def url(self, new_url):
        self._url = new_url

    @abstractmethod
    def attempt_booking(self):
        """Abstract method for attempt to make a booking."""

    @property
    def response(self):
        return self._response



class TennisScheduler(Scheduler):
    def __init__(self, reservation_date: dt.date, park_location: str = 'lyle') -> None:
        """Instantiate class."""
        super().__init__()

        # set and validate reservation date
        self.reservation_date = reservation_date
        max_res_date = dt.date.today() + dt.timedelta(days=14)
        if self.reservation_date > max_res_date:
            log.warning(f'Reservation date {self.reservation_date} too far in future; defaulting '
                        f'to max reservation date of 2 weeks from now ({max_res_date})')
            self.reservation_date = max_res_date
        
        # set and validate park location
        self.park_location = park_location
        if self.park_location not in ('lyle', 'stratford'):
            raise ValueError(f'Park location {self.park_location} not supported.')

        # construct URL
        self.url = f'https://{park_location}.newhamparkstennis.org.uk/Booking/BookByDate#?date={reservation_date}&role=member'

    @property
    def response(self):
        """Response regarding booking confirmed."""
        return

    def attempt_booking(self):
        """Attempt to book reservation."""

if __name__ == '__main__':
    main()

