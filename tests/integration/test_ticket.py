from datetime import date, datetime

import pytest

from datetime_interval_calculator import (
    DateTimeInterval,
    TicketIntervalCalculator,
    WorkingHoursCalendar,
)

pytestmark = pytest.mark.integration


def test_ticket_calendar_and_overlapping_exclusions():
    def interval(start, end):
        return DateTimeInterval(
            datetime.fromisoformat(start), datetime.fromisoformat(end), "Europe/Belgrade"
        )

    ticket = interval("2026-10-09T16:00", "2026-10-13T12:00")
    calendar = WorkingHoursCalendar(holidays=[date(2026, 10, 12)], timezone="Europe/Belgrade")
    calculator = TicketIntervalCalculator(calendar)
    pauses = [
        interval("2026-10-13T09:30", "2026-10-13T10:30"),
        interval("2026-10-13T10:00", "2026-10-13T11:00"),
    ]
    result = calculator.calculate_interval(ticket, pauses)
    assert result.length_seconds() == 9000
    assert len(result.to_timestamps()) == 3
    assert calculator.calculate_seconds(ticket, pauses) == 9000
    assert calculator.length_seconds(result) == 9000


def test_without_calendar():
    calculator = TicketIntervalCalculator()
    ticket = DateTimeInterval(0, 100)
    assert calculator.calculate_seconds(ticket, [DateTimeInterval(20, 40)]) == 80
    assert calculator.exclude_intervals(ticket, [ticket]).empty
