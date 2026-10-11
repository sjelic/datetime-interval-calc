# Datetime Interval Calculator

A standard Python package built on `portion`, with integer UTC timestamps,
local datetime display, exclusions, and working-calendar ticket durations.
Requires Python 3.10 or newer. `tzdata` supplies IANA timezones on Windows and
systems without an operating-system timezone database.

## Installation

```sh
python -m pip install .
# Development
python -m pip install -e '.[dev]'
python -m pytest
python -m build
```

The distribution name is `datetime-interval-calculator`; the import name is
`datetime_interval_calculator`. Once the repository is available:

```sh
python -m pip install git+https://github.com/sjelic/datetime-interval-calc.git
```

## Example

```python
from datetime import date, datetime, time
from datetime_interval_calculator import (
    DateTimeInterval,
    TicketIntervalCalculator,
    WorkingHoursCalendar,
    exclude_intervals,
    interval_length_seconds,
)

ticket = DateTimeInterval(
    datetime(2026, 10, 9, 16),
    datetime(2026, 10, 13, 12),
    timezone="Europe/Belgrade",
    datetime_format="%Y-%m-%d %H:%M %z",
)
calendar = WorkingHoursCalendar(
    working_days=range(5),  # Monday=0, Sunday=6
    working_hours=[(time(9), time(17))],
    holidays=[date(2026, 10, 12)],
    timezone="Europe/Belgrade",
)
pauses = [
    DateTimeInterval(
        datetime(2026, 10, 13, 9, 30),
        datetime(2026, 10, 13, 11),
        timezone="Europe/Belgrade",
    )
]
calculator = TicketIntervalCalculator(calendar)
remaining = calculator.calculate_interval(ticket, pauses)
print(remaining)  # Three disjoint datetime spans
print(remaining.to_timestamps())  # list[tuple[int, int]] in UTC seconds
print(calculator.calculate_seconds(ticket, pauses))  # 9000

# Without a working calendar:
remaining = exclude_intervals(ticket, pauses)
seconds = interval_length_seconds(remaining)
# Calendar exclusions can also be supplied explicitly:
remaining = exclude_intervals(ticket, [calendar.non_working_intervals(ticket), *pauses])
```

## Semantics and public API

- `DateTimeInterval(start, end, timezone="UTC", datetime_format=...)` accepts
  whole-second `datetime` values or integer Unix timestamps. Naive datetimes
  are interpreted in the named timezone using `zoneinfo.ZoneInfo`; aware
  datetimes preserve their instant. Booleans, floats, subsecond datetimes, and
  reversed intervals are rejected. Zero-length intervals are empty.
- All sets use **half-open `[start, end)`** bounds. Seconds measure elapsed
  time (`end - start`), rather than a count of timestamp labels. This prevents
  duplicate endpoints when adjacent shifts are joined. The requested closed
  notation `[start,end]` has the same elapsed duration, but this package uses
  the half-open convention consistently for subtraction and membership.
- `interval` exposes the underlying `portion.Interval`.
  `from_portion` accepts finite half-open integer interval sets. `|`, `&`, and
  `-` preserve the left operand's display timezone and format. Iteration yields
  individual wrapped intervals; `to_timestamps` returns sorted disjoint pairs.
- `exclude_intervals(interval, excluded_intervals)` subtracts their union;
  overlapping, duplicate, empty, and out-of-range exclusions work naturally.
  Both input and result may contain multiple disjoint intervals.
- `interval_length_seconds(interval)` and `interval.length_seconds()` return
  integer elapsed seconds summed across normalized components.
- `WorkingHoursCalendar` accepts working weekdays, a common sequence of
  `(datetime.time, datetime.time)` shifts, or a weekday-to-shifts mapping.
  Missing mapping entries have no working hours. Multiple shifts and overlapping
  shifts are supported; overlapping time is counted once.
- A shift with end before start spans midnight; equal endpoints mean 24 hours.
  A shift belongs to its starting weekday. An overnight shift starting on a
  holiday is suppressed, and holiday dates also remove any incoming spillover.
  Holidays must be `datetime.date` values, not strings or datetimes.
- `working_intervals(interval)` and `non_working_intervals(interval)` return
  clipped interval sets. `non_working_hours` aliases the latter and returns a
  set, not a numeric hours count. Empty schedules represent no working time.
- `TicketIntervalCalculator(calendar=None)` exposes `calculate_interval`,
  `calculate_seconds`, `exclude_intervals`, and `length_seconds`.
  Calculations subtract explicit exclusions and intersect with working time.

## Daylight-saving time

Durations are computed in UTC, so a full local day may contain 23 or 25 hours.
Ambiguous local datetimes honor `datetime.fold` (default 0, first occurrence).
Schedule boundaries honor `time.fold` as well. Nonexistent local times, such
as 02:30 during a spring clock jump, raise `ValueError` rather than shifting
silently. Supply aware instants or choose valid shift boundaries for such dates.

## Verification

Unit tests cover interval algebra, bounds, display, timezones, schedules,
holidays, overnight shifts, and DST. Integration tests combine ticket pauses
and calendars. CI runs lint, formatting, tests, builds a wheel and sdist, and
runs tests against the wheel in an isolated environment on Python 3.10–3.14.

```sh
python -m ruff check .
python -m ruff format --check .
python -m pytest --cov=datetime_interval_calculator --cov-report=term-missing
```

Licensed under the MIT license; see `LICENSE`.
