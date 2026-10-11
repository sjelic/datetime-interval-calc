from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import portion as P
import pytest

from datetime_interval_calculator import DateTimeInterval as D
from datetime_interval_calculator import exclude_intervals, interval_length_seconds


@pytest.mark.parametrize(
    "exclusions,expected",
    [
        ([], [(0, 100)]),
        ([(20, 40)], [(0, 20), (40, 100)]),
        ([(20, 50), (40, 60)], [(0, 20), (60, 100)]),
        ([(-10, 10), (90, 200)], [(10, 90)]),
        ([(0, 100)], []),
        ([(100, 120)], [(0, 100)]),
        ([(20, 40), (40, 60)], [(0, 20), (60, 100)]),
        ([(20, 40), (20, 40)], [(0, 20), (40, 100)]),
    ],
)
def test_subtraction(exclusions, expected):
    result = exclude_intervals(D(0, 100), (D(a, b) for a, b in exclusions))
    assert result.to_timestamps() == expected
    assert interval_length_seconds(result) == sum(b - a for a, b in expected)


def test_union_and_intersection():
    interval = D(0, 20) | D(10, 30) | D(40, 50)
    assert interval.length_seconds() == 40
    assert (interval & D(15, 45)).to_timestamps() == [(15, 30), (40, 45)]
    assert len(list(interval)) == 2
    assert D(0, 0).empty
    assert D(0, 0).length_seconds() == 0
    assert str(D(0, 0)) == "∅"


def test_timezone_and_format():
    interval = D(datetime(2026, 1, 1, 9), datetime(2026, 1, 1, 10), "Europe/Belgrade", "%H:%M %z")
    assert str(interval) == "[09:00 +0100, 10:00 +0100)"
    assert interval.length_seconds() == 3600
    assert interval == D(
        datetime(2026, 1, 1, 8, tzinfo=timezone.utc), datetime(2026, 1, 1, 9, tzinfo=timezone.utc)
    )
    assert (interval - D(0, 1)).datetime_format == "%H:%M %z"


@pytest.mark.parametrize(
    "a,b,error",
    [
        (2, 1, ValueError),
        (True, 2, TypeError),
        (0.5, 2, TypeError),
        ("today", 2, TypeError),
        (datetime(2026, 1, 1, microsecond=1), 2, ValueError),
    ],
)
def test_invalid_bounds(a, b, error):
    with pytest.raises(error):
        D(a, b)


@pytest.mark.parametrize(
    "interval", [P.closed(0, 1), P.open(0, 1), P.closedopen(0.5, 2), P.closedopen(0, P.inf)]
)
def test_invalid_portion(interval):
    with pytest.raises(ValueError):
        D.from_portion(interval)


def test_portion_empty_and_bad_exclusions():
    assert D.from_portion(P.empty()).empty
    with pytest.raises(TypeError):
        D.from_portion("x")
    with pytest.raises(TypeError):
        exclude_intervals(D(0, 1), [1])
    assert D(0, 1) != 1


def test_dst_fold_and_gap():
    tz = ZoneInfo("Europe/Belgrade")
    first = datetime(2026, 10, 25, 2, 30, tzinfo=tz, fold=0)
    second = first.replace(fold=1)
    assert D(first, second).length_seconds() == 3600
    with pytest.raises(ValueError, match="Nonexistent"):
        D(datetime(2026, 3, 29, 2, 30), datetime(2026, 3, 29, 4), "Europe/Belgrade")


def test_negative_timestamps_and_disjoint_subtraction():
    assert D(-10, 0).length_seconds() == 10
    assert exclude_intervals(D(0, 10) | D(20, 30), [D(5, 25)]).to_timestamps() == [(0, 5), (25, 30)]
