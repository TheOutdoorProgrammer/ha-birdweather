"""Bat detections preserve their identity, metadata and alert progress."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.birdweather.const import (
    BAT_BEHAVIORS,
    CONF_ALERT_MIN_CONFIDENCE,
    CONF_RECENT_WINDOW_HOURS,
    DOMAIN,
    EVENT_BIRDWEATHER,
    LAST_DETECTION_EVENT_LIMIT,
    TRIGGER_BAT_DETECTED,
)
from custom_components.birdweather.normalize import (
    _build_recent_events,
    _normalise_detections,
)

from .coordinator_helpers import make_client, make_coordinator

_START = datetime(2026, 9, 17, 12, tzinfo=UTC)


def _bat(detection_id: str, minutes: int = 1, **fields) -> dict:
    return {
        "detection_id": detection_id,
        "species_id": "8100",
        "species": "Big Brown Bat",
        "scientific_name": "Eptesicus fuscus",
        "classification": "bat",
        "last_seen": (_START + timedelta(minutes=minutes)).isoformat(),
        "confidence": 0.9,
        "behavior_code": "bat_feeding_buzz",
        "behavior": "Feeding buzz",
        "behavior_confidence": 0.7,
        "shortlist": [{"species_id": "8100", "species": "Big Brown Bat", "weight": 0.85}],
        **fields,
    }


def _raw(event: dict) -> dict:
    return {
        **event,
        "cn": event["species"],
        "sn": event.get("scientific_name", ""),
        "dt": event["last_seen"],
        "spCode": event.get("sp_code", ""),
        "image": event.get("image_url"),
    }


@pytest.fixture
def coordinator(hass: HomeAssistant):
    entry = MockConfigEntry(domain=DOMAIN, unique_id="12345")
    entry.add_to_hass(hass)
    dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={(DOMAIN, "12345")}
    )
    return make_coordinator(hass=hass, _bat_store=AsyncMock())


@pytest.fixture
def fired(hass: HomeAssistant) -> list:
    events = []
    hass.bus.async_listen(EVENT_BIRDWEATHER, lambda event: events.append(event.data))
    return events


@pytest.fixture
def clock():
    with patch("custom_components.birdweather.coordinator.datetime", wraps=datetime) as mocked:
        mocked.now.return_value = _START
        yield mocked


@pytest.mark.parametrize("initial", [[], [_bat("old", -5)]])
async def test_first_bat_poll_establishes_silent_baseline(
    coordinator, fired: list, clock, hass: HomeAssistant, initial: list
) -> None:
    await coordinator._update_bats(initial)
    await hass.async_block_till_done()

    assert fired == []
    assert coordinator._bat_state["events"] == initial
    coordinator._bat_store.async_save.assert_awaited_once()

    await coordinator._update_bats([_bat("new")])
    await hass.async_block_till_done()
    assert sorted(event["type"] for event in fired) == sorted([TRIGGER_BAT_DETECTED, "bat_feeding_buzz"])


@pytest.mark.parametrize("behavior", [*BAT_BEHAVIORS, None, "unrecognized_behavior"])
async def test_new_bat_emits_detection_and_only_recognized_behavior(
    coordinator, fired: list, clock, hass: HomeAssistant, behavior: str | None
) -> None:
    await coordinator._update_bats([])
    event = _bat("new", behavior_code=behavior)
    await coordinator._update_bats([event])
    await hass.async_block_till_done()

    expected = [TRIGGER_BAT_DETECTED]
    if behavior in BAT_BEHAVIORS:
        expected.append(behavior)
    assert sorted(item["type"] for item in fired) == sorted(expected)
    for item in fired:
        assert item["detection_id"] == "new"
        assert item["classification"] == "bat"
        assert item["behavior_confidence"] == 0.7
        assert item["shortlist"][0]["weight"] == 0.85


async def test_repeat_poll_and_restart_do_not_replay_bat_alerts(
    coordinator, fired: list, clock, hass: HomeAssistant
) -> None:
    await coordinator._update_bats([])
    event = _bat("first")
    await coordinator._update_bats([event])
    await coordinator._update_bats([event])
    await hass.async_block_till_done()
    assert len(fired) == 2

    persisted = deepcopy(coordinator._bat_store.async_save.call_args.args[0])
    reloaded = make_coordinator(hass=hass)
    reloaded._bat_store = AsyncMock()
    reloaded._bat_store.async_load.return_value = persisted
    await reloaded._load_stores()
    await reloaded._update_bats([event])
    await hass.async_block_till_done()
    assert len(fired) == 2
    assert reloaded._bat_state["events"] == [event]

    simultaneous = _bat("second", species_id="8101", species="Myotis")
    await reloaded._update_bats([event, simultaneous])
    await reloaded._update_bats([event, simultaneous])
    await hass.async_block_till_done()
    assert [item["detection_id"] for item in fired] == ["first", "first", "second", "second"]


async def test_confidence_gate_consumes_low_confidence_without_later_replay(
    coordinator, fired: list, clock, hass: HomeAssistant
) -> None:
    coordinator.config_entry.options[CONF_ALERT_MIN_CONFIDENCE] = 80
    await coordinator._update_bats([])
    events = [
        _bat("low", 1, confidence=0.4),
        _bat("threshold", 2, confidence=0.8, behavior_confidence=0.1),
        _bat("missing", 3, confidence=None),
    ]
    await coordinator._update_bats(events)
    await hass.async_block_till_done()

    assert [event["detection_id"] for event in fired] == ["threshold", "threshold"]
    assert len(coordinator._bat_state["events"]) == 3
    coordinator.config_entry.options[CONF_ALERT_MIN_CONFIDENCE] = 0
    await coordinator._update_bats(events)
    await hass.async_block_till_done()
    assert len(fired) == 2


async def test_bird_behavior_never_fires_bat_trigger(
    coordinator, fired: list, clock, hass: HomeAssistant
) -> None:
    await coordinator._update_bats([])
    await coordinator._update_bats([_bat("bird", classification="avian")])
    await hass.async_block_till_done()
    assert fired == []
    assert coordinator._bat_state["events"] == []


async def test_last_bat_survives_birds_filling_generic_buffer(
    coordinator, clock, hass: HomeAssistant
) -> None:
    bat = _raw(_bat("bat", -90, image_url="https://example.com/bat.jpg"))
    coordinator._client = make_client(detections={"detections": [bat]})
    first = await coordinator._async_update_data()
    assert first["last_bat_detection"]["detection_id"] == "bat"
    assert first["recent_bats"] == []

    birds = [_raw(_bat(
        f"bird-{i}", -1, classification="avian", species="American Robin",
        species_id="42", sp_code="amerob", behavior_code=None,
    )) for i in range(LAST_DETECTION_EVENT_LIMIT + 1)]
    coordinator.config_entry.options[CONF_RECENT_WINDOW_HOURS] = 2
    coordinator._client.get_raw_detections.return_value = {"detections": birds + [bat]}
    second = await coordinator._async_update_data()
    assert all(event["classification"] == "avian" for event in second["recent_events"])
    assert second["last_bat_detection"]["detection_id"] == "bat"
    assert second["last_bat_detection"]["image_url"] == "https://example.com/bat.jpg"
    assert len(second["recent_bats"]) == 1

    coordinator._client.get_raw_detections.return_value = {"detections": []}
    third = await coordinator._async_update_data()
    await hass.async_block_till_done()
    assert third["recent_bats"] == []
    assert third["last_bat_detection"]["detection_id"] == "bat"


@pytest.mark.parametrize("with_detection_ids", [True, False])
def test_simultaneous_taxa_keep_distinct_event_and_species_identities(with_detection_ids: bool) -> None:
    records = [_raw(_bat("a")), _raw(_bat("b", species_id="8101", species="Myotis"))]
    if not with_detection_ids:
        for record in records:
            record.pop("detection_id")
    raw = {"detections": records}
    events = _build_recent_events(raw, {}, 0, lambda _: None, 50)
    coordinator = make_coordinator()
    coordinator._merge_event_buffer(events)
    coordinator._merge_event_buffer(events)

    assert len(coordinator._event_buffer) == 2
    assert {event["species_id"] for event in coordinator._event_buffer} == {"8100", "8101"}
    assert len(_normalise_detections(raw)) == 2


def test_event_uses_cached_bat_image_without_ebird_code() -> None:
    cached = {"birdweather:8100": "https://example.com/cached.jpg"}
    events = _build_recent_events({"detections": [_raw(_bat("a"))]}, {}, 0, cached.get, 50)
    assert events[0]["image_url"] == "https://example.com/cached.jpg"
