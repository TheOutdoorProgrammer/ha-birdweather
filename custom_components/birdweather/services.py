"""Response actions for on-demand wildlife reports."""

from __future__ import annotations

import asyncio
import logging
from time import monotonic

import voluptuous as vol
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse, callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv

from .client import BirdWeatherError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


@callback
def async_register_services(hass: HomeAssistant) -> None:
    """Register once, resolving a currently loaded station on each call."""
    async def get_activity(call: ServiceCall) -> dict:
        entry = hass.config_entries.async_get_entry(call.data["config_entry_id"])
        if entry is None or entry.domain != DOMAIN or entry.state is not ConfigEntryState.LOADED:
            raise ServiceValidationError("Select a loaded BirdWeather integration entry")
        started = monotonic()
        try:
            async with asyncio.timeout(60):
                result = await entry.runtime_data.async_get_activity(
                    call.data["start"], call.data["end"]
                )
        except ValueError as err:
            raise ServiceValidationError(str(err)) from err
        except (BirdWeatherError, TimeoutError) as err:
            _LOGGER.warning("BirdWeather activity query failed", extra={
                "operation": "get_activity", "outcome": "error",
                "error_type": type(err).__name__,
            })
            raise HomeAssistantError("BirdWeather activity is unavailable; try again later") from err
        _LOGGER.info("BirdWeather activity query finished", extra={
            "operation": "get_activity",
            "outcome": "complete" if result["complete"] else "incomplete",
            "pages": result["pages"], "reason": result["reason"],
            "duration_ms": round((monotonic() - started) * 1000),
        })
        return result

    hass.services.async_register(
        DOMAIN, "get_activity", get_activity,
        schema=vol.Schema({
            vol.Required("config_entry_id"): cv.string,
            vol.Required("start"): cv.datetime,
            vol.Required("end"): cv.datetime,
        }),
        supports_response=SupportsResponse.ONLY,
    )
