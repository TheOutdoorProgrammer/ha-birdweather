"""Exercise the real HA service registry and station coordinator boundary."""

from unittest.mock import AsyncMock

import pytest
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from custom_components.birdweather.client import BirdWeatherError
from custom_components.birdweather.services import async_register_services

from .test_activity import END, START
from .test_entry_setup import _setup_entry


async def call_activity(hass, entry_id):
    return await hass.services.async_call("birdweather", "get_activity", {
        "config_entry_id": entry_id, "start": START.isoformat(), "end": END.isoformat(),
    }, blocking=True, return_response=True)


async def test_activity_action_reuses_station_client(hass):
    entry = await _setup_entry(hass)
    expected = {"complete": True, "pages": 1, "reason": None, "total_count": 2}
    client = entry.runtime_data._client
    client.get_activity = AsyncMock(return_value=expected)
    async_register_services(hass)
    assert await call_activity(hass, entry.entry_id) == expected
    client.get_activity.assert_awaited_once_with("12345", START, END)


async def test_unloaded_or_missing_entry_rejected(hass):
    entry = await _setup_entry(hass)
    async_register_services(hass)
    await hass.config_entries.async_unload(entry.entry_id)
    for entry_id in (entry.entry_id, "missing"):
        with pytest.raises(ServiceValidationError, match="loaded BirdWeather"):
            await call_activity(hass, entry_id)


@pytest.mark.parametrize("error", [BirdWeatherError("offline"), TimeoutError()])
async def test_api_failures_propagate_without_empty_success(hass, error):
    entry = await _setup_entry(hass)
    entry.runtime_data._client.get_activity = AsyncMock(side_effect=error)
    async_register_services(hass)
    with pytest.raises(HomeAssistantError, match="activity is unavailable"):
        await call_activity(hass, entry.entry_id)


async def test_window_validation_becomes_user_error(hass):
    entry = await _setup_entry(hass)
    entry.runtime_data._client.get_activity = AsyncMock(side_effect=ValueError("bad interval"))
    async_register_services(hass)
    with pytest.raises(ServiceValidationError, match="bad interval"):
        await call_activity(hass, entry.entry_id)


async def test_incomplete_response_is_preserved(hass):
    entry = await _setup_entry(hass)
    expected = {"complete": False, "pages": 100, "reason": "page_limit", "total_count": None}
    entry.runtime_data._client.get_activity = AsyncMock(return_value=expected)
    async_register_services(hass)
    assert await call_activity(hass, entry.entry_id) == expected
