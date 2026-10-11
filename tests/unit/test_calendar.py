from datetime import date, datetime, time

import pytest

from datetime_interval_calculator import DateTimeInterval as D
from datetime_interval_calculator import WorkingHoursCalendar as C


def span(a, b):
    return D(datetime.fromisoformat(a), datetime.fromisoformat(b), "Europe/Belgrade")


def test_weekends_holidays_and_clipping():
    calendar = C(holidays=[date(2026, 10, 12)], timezone="Europe/Belgrade")
    ticket = span("2026-10-09T16:00", "2026-10-13T10:00")
    working = calendar.working_intervals(ticket)
    nonworking = calendar.non_working_hours(ticket)
    assert working.length_seconds() == 2 * 3600
    assert (working & nonworking).empty
    assert working | nonworking == ticket


def test_split_shifts_weekday_schedule_overlap():
    calendar = C(
        working_hours={0: [(time(9), time(12)), (time(11), time(13)), (time(14), time(17))]},
        timezone="Europe/Belgrade",
    )
    ticket = span("2026-10-12T00:00", "2026-10-14T00:00")
    result = calendar.working_intervals(ticket)
    assert result.length_seconds() == 7 * 3600
    assert len(list(result)) == 2


def test_overnight_and_holiday_spillover():
    calendar = C([0], [(time(22), time(6))], timezone="Europe/Belgrade")
    ticket = span("2026-10-13T01:00", "2026-10-13T05:00")
    assert calendar.working_intervals(ticket).length_seconds() == 4 * 3600
    holiday = C([0], [(time(22), time(6))], [date(2026, 10, 13)], "Europe/Belgrade")
    assert holiday.working_intervals(ticket).empty
    holiday_start = C([0], [(time(22), time(6))], [date(2026, 10, 12)], "Europe/Belgrade")
    assert holiday_start.working_intervals(ticket).empty


@pytest.mark.parametrize("day,hours", [("2026-03-29", 23), ("2026-10-25", 25)])
def test_dst_actual_elapsed_seconds(day, hours):
    calendar = C([6], [(time(0), time(0))], timezone="Europe/Belgrade")
    end = "2026-03-30" if hours == 23 else "2026-10-26"
    ticket = span(day + "T00:00", end + "T00:00")
    assert calendar.working_intervals(ticket).length_seconds() == hours * 3600


def test_disjoint_and_empty():
    calendar = C(timezone="Europe/Belgrade")
    ticket = span("2026-10-12T09:00", "2026-10-12T10:00") | span(
        "2026-10-12T16:00", "2026-10-12T18:00"
    )
    assert calendar.working_intervals(ticket).length_seconds() == 2 * 3600
    assert calendar.working_intervals(D(0, 0)).empty
    assert C([]).working_intervals(D(0, 100)).empty


@pytest.mark.parametrize(
    "kwargs,error",
    [
        ({"working_days": [7]}, ValueError),
        ({"working_days": [True]}, ValueError),
        ({"working_hours": {7: []}}, ValueError),
        ({"holidays": ["2026-01-01"]}, TypeError),
        ({"holidays": [datetime(2026, 1, 1)]}, TypeError),
        ({"working_hours": [("09:00", time(17))]}, TypeError),
        ({"working_hours": [(time(9, microsecond=1), time(17))]}, ValueError),
    ],
)
def test_invalid_calendar(kwargs, error):
    with pytest.raises(error):
        C(**kwargs)


def test_nonexistent_shift_boundary():
    calendar = C([6], [(time(2, 30), time(4))], timezone="Europe/Belgrade")
    with pytest.raises(ValueError, match="Nonexistent"):
        calendar.working_intervals(span("2026-03-29T00:00", "2026-03-30T00:00"))
