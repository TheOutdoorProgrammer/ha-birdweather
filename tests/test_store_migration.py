"""The five legacy cold-map .storage files migrate into one species_meta store."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.birdweather.const import (
    CONF_STATION_ID,
    CONF_STATION_NAME,
    DOMAIN,
)
from custom_components.birdweather.coordinator import BirdWeatherCoordinator

SID = "777"


def _entry(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id=SID,
        data={CONF_STATION_ID: SID, CONF_STATION_NAME: "X"},
    )
    entry.add_to_hass(hass)
    return entry


async def test_legacy_cold_maps_consolidate_into_species_meta(
    hass: HomeAssistant, hass_storage
) -> None:
    # Seed two legacy per-map stores; species_meta is absent (pre-upgrade state).
    await Store(hass, 1, f"{DOMAIN}.{SID}.sp_codes").async_save({"Robin": "amerob"})
    await Store(hass, 1, f"{DOMAIN}.{SID}.links").async_save(
        {"amerob": {"ebird_url": "e"}}
    )

    coord = BirdWeatherCoordinator(hass, _entry(hass))
    await coord._load_stores()

    # Migrated into the in-memory maps...
    assert coord._sp_codes == {"Robin": "amerob"}
    assert coord._links_cache == {"amerob": {"ebird_url": "e"}}
    # ...written to the consolidated store...
    assert f"{DOMAIN}.{SID}.species_meta" in hass_storage
    meta = hass_storage[f"{DOMAIN}.{SID}.species_meta"]["data"]
    assert meta["sp_codes"] == {"Robin": "amerob"}
    assert meta["links"] == {"amerob": {"ebird_url": "e"}}
    # ...and the legacy per-map files are removed.
    for legacy in ("sp_codes", "sci_names", "image_urls", "image_attr", "links"):
        assert f"{DOMAIN}.{SID}.{legacy}" not in hass_storage


async def test_species_meta_is_authoritative_when_present(
    hass: HomeAssistant, hass_storage
) -> None:
    # When species_meta exists, it's used directly (no migration from legacy).
    await Store(hass, 1, f"{DOMAIN}.{SID}.species_meta").async_save(
        {"sp_codes": {"Owl": "brdowl"}, "sci_names": {}, "image_urls": {},
         "image_attr": {}, "links": {}}
    )
    coord = BirdWeatherCoordinator(hass, _entry(hass))
    await coord._load_stores()
    assert coord._sp_codes == {"Owl": "brdowl"}


async def test_bat_metadata_survives_restart_without_a_bird_code(hass, hass_storage):
    entry = _entry(hass)
    coord = BirdWeatherCoordinator(hass, entry)
    record = {
        "species": "Big Brown Bat", "species_id": "17300", "classification": "bat",
        "scientific_name": "Eptesicus fuscus", "sp_code": "",
        "image_url": "https://example.com/bat.jpg", "image_credit": "Photographer",
        "image_license": "CC BY-SA 4.0", "wikipedia_url": "https://en.wikipedia.org/wiki/Big_brown_bat",
        "birdweather_url": "https://app.birdweather.com/species/big-brown-bat",
    }
    assert coord._cache_species_metadata(record)
    await coord._save_meta()

    restored = BirdWeatherCoordinator(hass, entry)
    await restored._load_stores()
    view = restored._with_links([{"species": "Big Brown Bat"}])[0]
    for field in ("species_id", "classification", "image_url", "image_credit", "image_license",
                  "scientific_name", "wikipedia_url", "birdweather_url"):
        assert view[field] == record[field]
    for field in ("ebird_url", "macaulay_url", "allaboutbirds_url"):
        assert view[field] is None


async def test_legacy_bird_cache_is_available_after_species_id_upgrade(hass):
    coord = BirdWeatherCoordinator(hass, _entry(hass))
    coord._image_urls["amerob"] = "https://example.com/robin.jpg"
    coord._image_attr["amerob"] = {"image_credit": "Legacy photographer"}
    coord._links_cache["amerob"] = {"wikipedia_url": "https://en.wikipedia.org/wiki/American_robin"}
    coord._cache_species_metadata({
        "species": "American Robin", "sp_code": "amerob",
        "species_id": "100", "classification": "avian",
    })
    view = coord._with_links([{"species": "American Robin"}])[0]
    assert view["image_url"] == "https://example.com/robin.jpg"
    assert view["image_credit"] == "Legacy photographer"
    assert view["wikipedia_url"] == "https://en.wikipedia.org/wiki/American_robin"
    assert view["ebird_url"] == "https://ebird.org/species/amerob"


async def test_legacy_event_upgrades_id_across_equivalent_timezone_offsets(hass):
    coord = BirdWeatherCoordinator(hass, _entry(hass))
    coord._event_buffer = [{"species": "Big Brown Bat", "sp_code": "", "last_seen": "2026-09-17T12:00:00Z"}]
    coord._merge_event_buffer([
        {"species": "Big Brown Bat", "species_id": "100", "detection_id": "a", "last_seen": "2026-09-17T08:00:00-04:00"},
        {"species": "Silver-haired Bat", "species_id": "101", "detection_id": "b", "last_seen": "2026-09-17T12:00:00Z"},
    ])
    assert {event["detection_id"] for event in coord._event_buffer} == {"a", "b"}
