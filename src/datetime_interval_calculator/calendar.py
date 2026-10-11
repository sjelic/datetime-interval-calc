"""Local working schedules and date-based holidays."""

from datetime import date, datetime, time, timedelta
from typing import Iterable, Mapping
from zoneinfo import ZoneInfo

from .interval import DEFAULT_FORMAT, DateTimeInterval


class WorkingHoursCalendar:
    """Working weekdays (Monday=0), local shifts, and full-date holidays.

    working_hours is a common sequence of (start, end) time pairs, or a mapping
    of weekday to that sequence. End <= start denotes an overnight shift;
    equal endpoints denote 24 hours. Overnight shifts belong to their start day.
    Holidays remove all time on that local date, including overnight spillover.
    Ambiguous schedule boundaries use fold=0 unless time.fold is set explicitly;
    nonexistent boundaries raise ValueError when encountered.
    """

    def __init__(
        self,
        working_days: Iterable[int] = range(5),
        working_hours: Iterable[tuple[time, time]] | Mapping[int, Iterable[tuple[time, time]]] = (
            (time(9), time(17)),
        ),
        holidays: Iterable[date] = (),
        timezone: str = "UTC",
        datetime_format: str = DEFAULT_FORMAT,
    ):
        self.timezone = ZoneInfo(timezone)
        self.datetime_format = datetime_format
        self.working_days = frozenset(working_days)
        if any(type(day) is not int or day not in range(7) for day in self.working_days):
            raise ValueError("Working days must be integers from 0 to 6")
        self.holidays = frozenset(holidays)
        if any(type(day) is not date for day in self.holidays):
            raise TypeError("Holidays must be datetime.date instances")
        if isinstance(working_hours, Mapping):
            if any(type(day) is not int or day not in range(7) for day in working_hours):
                raise ValueError("Schedule keys must be weekdays from 0 to 6")
            self.working_hours = {
                day: tuple(working_hours.get(day, ())) for day in self.working_days
            }
        else:
            shifts = tuple(working_hours)
            self.working_hours = dict.fromkeys(self.working_days, shifts)
        for shifts in self.working_hours.values():
            for start, end in shifts:
                if not isinstance(start, time) or not isinstance(end, time):
                    raise TypeError("Shift endpoints must be datetime.time instances")
                if start.tzinfo is not None or end.tzinfo is not None:
                    raise ValueError("Shift times must be naive local times")
                if start.microsecond or end.microsecond:
                    raise ValueError("Shift times must use whole seconds")

    def _span(self, start: datetime, end: datetime) -> DateTimeInterval:
        return DateTimeInterval(start, end, self.timezone.key, self.datetime_format)

    def working_intervals(self, interval: DateTimeInterval) -> DateTimeInterval:
        """Return working time clipped to the requested (possibly disjoint) set."""
        result = DateTimeInterval(0, 0, self.timezone.key, self.datetime_format)
        for lower, upper in interval.to_timestamps():
            first = datetime.fromtimestamp(lower, self.timezone).date() - timedelta(days=1)
            last = datetime.fromtimestamp(upper, self.timezone).date()
            day = first
            while day <= last:
                if day.weekday() in self.working_days and day not in self.holidays:
                    for start, end in self.working_hours[day.weekday()]:
                        end_day = day + timedelta(days=int(end <= start))
                        shift = self._span(
                            datetime.combine(day, start), datetime.combine(end_day, end)
                        )
                        result = result | (shift & interval)
                day += timedelta(days=1)
        for holiday in self.holidays:
            if any(
                datetime.fromtimestamp(a, self.timezone).date()
                <= holiday
                <= datetime.fromtimestamp(b, self.timezone).date()
                for a, b in interval.to_timestamps()
            ):
                result = result - self._span(
                    datetime.combine(holiday, time()),
                    datetime.combine(holiday + timedelta(days=1), time()),
                )
        return result

    def non_working_intervals(self, interval: DateTimeInterval) -> DateTimeInterval:
        return interval - self.working_intervals(interval)

    def non_working_hours(self, interval: DateTimeInterval) -> DateTimeInterval:
        """Alias returning interval sets, not a numeric hours count."""
        return self.non_working_intervals(interval)
