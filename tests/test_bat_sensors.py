"""Bat sensor attributes remain usable alongside the ordinary bird feed."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from homeassistant.core import HomeAssistant

from custom_components.birdweather.const import CONF_STATION_ID
from custom_components.birdweather.sensor import (
    BirdWeatherLastBatDetectionSensor,
    BirdWeatherLastDetectionSensor,
    BirdWeatherRecentBatsSensor,
    async_setup_entry,
)

from .coordinator_helpers import make_coordinator

STATION_ID = "12345"


@pytest.fixture
def bat() -> dict:
    return {
        "detection_id": "932001",
        "species_id": "8123",
        "species": "Big Brown Bat",
        "scientific_name": "Eptesicus fuscus",
        "classification": "bat",
        "image_url": "https://example.com/bat.jpg",
        "behavior": "Feeding buzz",
        "behavior_code": "bat_feeding_buzz",
        "behavior_confidence": 0.82,
        "confidence": 0.94,
        "shortlist": [{
            "species_id": "8123",
            "species": "Big Brown Bat",
            "scientific_name": "Eptesicus fuscus",
            "classification": "bat",
            "weight": 0.72,
        }],
    }


def test_last_bat_keeps_metadata_when_latest_detection_is_bird(bat: dict) -> None:
    bird = {"species": "American Robin", "classification": "bird"}
    coordinator = make_coordinator(data={
        "last_bat_detection": bat,
        "bat_events": [bat],
        "last_detection": bird,
        "recent_events": [bird, bat],
    })
    sensor = BirdWeatherLastBatDetectionSensor(coordinator, STATION_ID)

    assert sensor.native_value == "Big Brown Bat"
    assert sensor.entity_picture == bat["image_url"]
    assert sensor.icon == "mdi:bat"
    assert sensor.unique_id == f"{STATION_ID}_last_bat_detection"
    attrs = sensor.extra_state_attributes
    assert attrs["detections"] == [bat]
    assert attrs["detection_id"] == "932001"
    assert attrs["species_id"] == "8123"
    assert attrs["classification"] == "bat"
    assert attrs["behavior"] == "Feeding buzz"
    assert attrs["behavior_code"] == "bat_feeding_buzz"
    assert attrs["behavior_confidence"] == 0.82
    assert attrs["confidence"] == 0.94
    assert attrs["shortlist"][0]["weight"] == 0.72
    assert BirdWeatherLastDetectionSensor(coordinator, STATION_ID).native_value == "American Robin"


def test_bird_metadata_can_have_no_bat_behavior_or_image() -> None:
    bird = {
        "species": "American Robin",
        "image_url": None,
        "behavior": None,
        "behavior_code": None,
        "behavior_confidence": None,
        "shortlist": [],
    }
    coordinator = make_coordinator(data={"last_detection": bird, "recent_events": [bird]})
    sensor = BirdWeatherLastDetectionSensor(coordinator, STATION_ID)

    assert sensor.native_value == "American Robin"
    assert sensor.entity_picture is None
    assert sensor.extra_state_attributes["behavior_code"] is None
    assert sensor.extra_state_attributes["behavior_confidence"] is None
    assert sensor.extra_state_attributes["shortlist"] == []
    assert sensor.extra_state_attributes["detections"] == [bird]
    assert sensor.unique_id == f"{STATION_ID}_last_detection"


def test_recent_bats_counts_identifications_including_broader_taxa(bat: dict) -> None:
    genus = {"species": "Myotis", "classification": "bat", "count": 12}
    coordinator = make_coordinator(data={"recent_bats": [{**bat, "count": 4}, genus]})
    sensor = BirdWeatherRecentBatsSensor(coordinator, STATION_ID)

    assert sensor.native_value == 2
    assert sensor.native_unit_of_measurement == "identifications"
    assert sensor.icon == "mdi:bat"
    assert sensor.unique_id == f"{STATION_ID}_recent_bats"
    assert sensor.extra_state_attributes["detections"][1]["count"] == 12

    coordinator.data["recent_bats"] = []
    assert sensor.native_value == 0
    assert sensor.extra_state_attributes == {"detections": []}


@pytest.mark.parametrize("data", [{}, {"last_bat_detection": None, "bat_events": [], "recent_bats": []}])
def test_station_without_bats_has_unknown_last_and_zero_recent(data: dict) -> None:
    coordinator = make_coordinator(data=data)
    last = BirdWeatherLastBatDetectionSensor(coordinator, STATION_ID)
    recent = BirdWeatherRecentBatsSensor(coordinator, STATION_ID)

    assert last.native_value is None
    assert last.entity_picture is None
    assert last.extra_state_attributes == {"detections": []}
    assert recent.native_value == 0


async def test_bat_entities_created_before_station_reports_bats(hass: HomeAssistant) -> None:
    coordinator = make_coordinator(data={})
    entry = SimpleNamespace(data={CONF_STATION_ID: STATION_ID}, runtime_data=coordinator)
    entities = []

    await async_setup_entry(hass, entry, entities.extend)

    unique_ids = {entity.unique_id for entity in entities}
    assert f"{STATION_ID}_last_bat_detection" in unique_ids
    assert f"{STATION_ID}_recent_bats" in unique_ids
    assert len(unique_ids) == len(entities)
