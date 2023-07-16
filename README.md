# Tennis court bookings

This is a Python module to make (fake) tennis court bookings. The core elements
of this module are based on the real process by which I make bookings at my
local tennis court.

## Usage

```python
>>> scheduler = TennisScheduler(
        booking_date=dt.date(2023, 7, 16),
        target_start_time=dt.time(10, 00),
        target_end_time=dt.time(12, 00),
        location=CourtLocation.ANY,
        include_paid_lighting_slots=True,
        exclude_one_hour_slots=True,
    )
>>> confirmation = scheduler.book()
>>> confirmation
BookingConfirmation(
    location=<CourtLocation.LYLE: 'lyle'>,
    court_number=1,
    booking_date=datetime.date(2023, 7, 16),
    booking_time=datetime.time(9, 0),
    length_in_hours=2,
)
```

```bash
$ python -m tennis.scheduler --location lyle --booking_date 2023-07-16 --target_start_time 10:00 --target_end_time 12:00 --exclude_one_hour_slots --include_paid_lighting_slots
INFO:root:Initialising tennis reservation bot.
INFO:root:Input arguments:
Args(booking_date=datetime.date(2023, 7, 16), target_start_time=datetime.time(10, 0), target_end_time=datetime.time(12, 0), location=<CourtLocation.LYLE: 'lyle'>, include_paid_lighting_slots=True, exclude_one_hour_slots=True)
INFO:root:Found 3 available slots.
INFO:root:Booking confirmed:
BookingConfirmation(location=<CourtLocation.LYLE: 'lyle'>, court_number=1, booking_date=datetime.date(2023, 7, 16), booking_time=datetime.time(9, 0), length_in_hours=2)
INFO:root:Scheduler exited successfully.
```

Note that the script assumes that there is a file in the local directory called
`conf.yml` that contains the following fields:


```yml
user:
  role_id: 1234567890

card:
  number: 0000000000000000
  name: Some card user name.
  cvv: 123
  exp_month: 1
  exp_year: 15
```
