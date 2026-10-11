"""Finite datetime interval sets backed by portion."""

from datetime import datetime
from datetime import timezone as dt_timezone
from typing import Iterable
from zoneinfo import ZoneInfo

import portion as P

DEFAULT_FORMAT = "%Y-%m-%d %H:%M:%S %Z%z"


def timestamp(value: int | datetime, timezone: ZoneInfo) -> int:
    """Convert a whole-second instant; naive datetimes use the named timezone.

    Ambiguous local times honor datetime.fold. Nonexistent local times are rejected.
    """
    if isinstance(value, bool):
        raise TypeError("Boolean is not a timestamp")
    if isinstance(value, int):
        return value
    if not isinstance(value, datetime):
        raise TypeError("Expected an integer UTC timestamp or datetime")
    if value.microsecond:
        raise ValueError("Subsecond datetimes are not supported")
    if value.tzinfo is None or value.utcoffset() is None:
        value = value.replace(tzinfo=timezone)
    local = value.astimezone(dt_timezone.utc).astimezone(value.tzinfo)
    if local.replace(tzinfo=None) != value.replace(tzinfo=None):
        raise ValueError("Nonexistent local datetime")
    return int(value.timestamp())


class DateTimeInterval:
    """A union of half-open intervals with UTC integer endpoints.

    Composition wraps portion.Interval rather than altering portion's bound semantics.
    """

    def __init__(
        self,
        start: int | datetime,
        end: int | datetime,
        timezone: str = "UTC",
        datetime_format: str = DEFAULT_FORMAT,
    ):
        self.timezone = ZoneInfo(timezone)
        self.datetime_format = datetime_format
        lower, upper = timestamp(start, self.timezone), timestamp(end, self.timezone)
        if lower > upper:
            raise ValueError("start must not be later than end")
        self._interval = P.closedopen(lower, upper)

    @classmethod
    def from_portion(
        cls, interval: P.Interval, timezone: str = "UTC", datetime_format: str = DEFAULT_FORMAT
    ) -> "DateTimeInterval":
        """Wrap an empty or finite half-open integer portion interval set."""
        if not isinstance(interval, P.Interval):
            raise TypeError("Expected portion.Interval")
        for atom in interval:
            if (
                type(atom.lower) is not int
                or type(atom.upper) is not int
                or atom.left != P.CLOSED
                or atom.right != P.OPEN
            ):
                raise ValueError("Expected finite half-open integer bounds")
        result = cls(0, 0, timezone, datetime_format)
        result._interval = interval
        return result

    @property
    def interval(self) -> P.Interval:
        return self._interval

    @property
    def empty(self) -> bool:
        return self._interval.empty

    def _wrap(self, interval: P.Interval) -> "DateTimeInterval":
        return self.from_portion(interval, self.timezone.key, self.datetime_format)

    def __or__(self, other: "DateTimeInterval") -> "DateTimeInterval":
        return self._wrap(self.interval | other.interval)

    def __and__(self, other: "DateTimeInterval") -> "DateTimeInterval":
        return self._wrap(self.interval & other.interval)

    def __sub__(self, other: "DateTimeInterval") -> "DateTimeInterval":
        return self._wrap(self.interval - other.interval)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, DateTimeInterval) and self.interval == other.interval

    def __iter__(self):
        for atom in self.interval:
            yield self._wrap(atom)

    def to_timestamps(self) -> list[tuple[int, int]]:
        return [(atom.lower, atom.upper) for atom in self.interval]

    def length_seconds(self) -> int:
        """Elapsed seconds across all disjoint components, counted once."""
        return sum(end - start for start, end in self.to_timestamps())

    def __str__(self) -> str:
        def display(value: int) -> str:
            return datetime.fromtimestamp(value, self.timezone).strftime(self.datetime_format)

        return " | ".join(f"[{display(a)}, {display(b)})" for a, b in self.to_timestamps()) or "∅"


def exclude_intervals(
    interval: DateTimeInterval, excluded_intervals: Iterable[DateTimeInterval]
) -> DateTimeInterval:
    """Subtract the union of exclusions, including overlaps and out-of-range spans."""
    excluded = P.empty()
    for item in excluded_intervals:
        if not isinstance(item, DateTimeInterval):
            raise TypeError("Exclusions must be DateTimeInterval instances")
        excluded |= item.interval
    return interval._wrap(interval.interval - excluded)


def interval_length_seconds(interval: DateTimeInterval) -> int:
    return interval.length_seconds()
