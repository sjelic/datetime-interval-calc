"""Ticket elapsed time after exclusions and optional working-calendar filtering."""

from typing import Iterable

from .calendar import WorkingHoursCalendar
from .interval import DateTimeInterval, exclude_intervals, interval_length_seconds


class TicketIntervalCalculator:
    def __init__(self, calendar: WorkingHoursCalendar | None = None):
        self.calendar = calendar

    @staticmethod
    def exclude_intervals(
        interval: DateTimeInterval, excluded_intervals: Iterable[DateTimeInterval] = ()
    ) -> DateTimeInterval:
        return exclude_intervals(interval, excluded_intervals)

    @staticmethod
    def length_seconds(interval: DateTimeInterval) -> int:
        return interval_length_seconds(interval)

    def calculate_interval(
        self, interval: DateTimeInterval, excluded_intervals: Iterable[DateTimeInterval] = ()
    ) -> DateTimeInterval:
        remaining = exclude_intervals(interval, excluded_intervals)
        if self.calendar is not None:
            remaining = remaining & self.calendar.working_intervals(interval)
        return remaining

    def calculate_seconds(
        self, interval: DateTimeInterval, excluded_intervals: Iterable[DateTimeInterval] = ()
    ) -> int:
        return self.calculate_interval(interval, excluded_intervals).length_seconds()
