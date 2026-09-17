"""Exact interval reports must distinguish complete history from a sample."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest

from custom_components.birdweather.client import BirdWeatherClient, BirdWeatherError

from .test_client_fetch import _Session

START = datetime(2026, 9, 16, 4, tzinfo=UTC)
END = START + timedelta(days=1)


def detection(identity, timestamp=None, classification="avian", species_id="robin"):
    return {
        "id": identity, "timestamp": (timestamp or START).isoformat(),
        "species": {"id": species_id, "commonName": "Wildlife", "classification": classification},
    }


def page(nodes, has_next=False, cursor=None):
    return {"station": {"detections": {
        "nodes": nodes, "pageInfo": {"hasNextPage": has_next, "endCursor": cursor},
    }}}


async def test_exact_interval_pages_dedupes_and_classifies():
    bat = detection("b", START + timedelta(hours=4), "bat", "bat")
    session = _Session([
        page([detection("before", START - timedelta(seconds=1)), detection("a"), bat], True, "one"),
        page([bat, detection("c", classification=None, species_id=None), detection("end", END)]),
    ])
    result = await BirdWeatherClient(session).get_activity("1", START, END)
    assert result["complete"] is True
    assert (result["bird_count"], result["bat_count"], result["other_count"], result["total_count"]) == (1, 1, 1, 3)
    assert len(result["species"]) == 2
    assert session.requests[0]["variables"]["period"] == {
        "from": "2026-09-16", "to": "2026-09-17", "timezone": "UTC",
    }
    assert session.requests[1]["variables"]["after"] == "one"


async def test_empty_accessible_station_is_complete_zero():
    result = await BirdWeatherClient(_Session(page([]))).get_activity("1", START, END)
    assert result["complete"] is True
    assert result["total_count"] == 0


async def test_missing_station_is_an_error_not_zero():
    with pytest.raises(BirdWeatherError):
        await BirdWeatherClient(_Session({"station": None})).get_activity("1", START, END)


@pytest.mark.parametrize("cursor", [None, "", 123])
async def test_invalid_cursor_is_incomplete(cursor):
    result = await BirdWeatherClient(_Session(page([detection("a")], True, cursor))).get_activity("1", START, END)
    assert result["complete"] is False
    assert result["total_count"] is None
    assert result["reason"] == "pagination_stalled"


@pytest.mark.parametrize("pages", [
    [page([detection("a")], True, "one"), page([detection("b")], True, "one")],
    [page([detection("a")], True, "one"), page([detection("a")], True, "two")],
    [page([detection("a")], True, "one"), page([], True, "two")],
])
async def test_stalled_pagination_never_claims_exact_counts(pages):
    result = await BirdWeatherClient(_Session(pages)).get_activity("1", START, END)
    assert result["reason"] == "pagination_stalled"
    assert result["bird_count"] is None


async def test_bounded_page_budget():
    with patch("custom_components.birdweather.client._ACTIVITY_MAX_PAGES", 1):
        result = await BirdWeatherClient(_Session(page([detection("a")], True, "one"))).get_activity("1", START, END)
    assert result["reason"] == "page_limit"
    assert result["total_count"] is None


@pytest.mark.parametrize("node", [
    None, {"id": "a"}, {**detection("a"), "timestamp": "invalid"},
    {**detection("a"), "timestamp": "2026-09-16T04:00:00"},
    {**detection("a"), "id": None}, detection("a", species_id=None),
])
async def test_invalid_records_never_disappear_as_zero(node):
    result = await BirdWeatherClient(_Session(page([node]))).get_activity("1", START, END)
    assert result["complete"] is False
    assert result["total_count"] is None


async def test_changed_duplicate_invalidates_report():
    result = await BirdWeatherClient(_Session([
        page([detection("a")], True, "one"), page([detection("a", classification="bat")]),
    ])).get_activity("1", START, END)
    assert result["reason"] == "changed_detection"


@pytest.mark.parametrize("connection", [None, {}, {"nodes": [], "pageInfo": {"hasNextPage": None}}])
async def test_invalid_response_is_not_empty_history(connection):
    result = await BirdWeatherClient(_Session({"station": {"detections": connection}})).get_activity("1", START, END)
    assert result["reason"] == "invalid_response"


@pytest.mark.parametrize(("start", "end"), [
    (START.replace(tzinfo=None), END), (START, END.replace(tzinfo=None)),
    (START, START), (END, START), (START, START + timedelta(days=8, seconds=1)),
])
async def test_bad_windows_rejected_without_request(start, end):
    session = _Session([])
    with pytest.raises(ValueError):
        await BirdWeatherClient(session).get_activity("1", start, end)
    assert session.requests == []


async def test_dst_window_and_exclusive_utc_midnight():
    start = datetime.fromisoformat("2026-11-01T00:00:00-04:00")
    end = datetime.fromisoformat("2026-11-02T00:00:00-05:00")
    session = _Session(page([detection("a", end - timedelta(seconds=1)), detection("b", end)]))
    result = await BirdWeatherClient(session).get_activity("1", start, end)
    assert result["total_count"] == 1
    assert datetime.fromisoformat(result["end"]) - datetime.fromisoformat(result["start"]) == timedelta(hours=25)
    midnight = datetime(2026, 9, 17, tzinfo=UTC)
    await BirdWeatherClient(session).get_activity("1", START, midnight)
    assert session.requests[-1]["variables"]["period"]["to"] == "2026-09-16"
