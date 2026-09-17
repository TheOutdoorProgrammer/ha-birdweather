from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from custom_components.birdweather import async_setup


async def test_shared_wildlife_module_is_served_without_being_injected(hass):
    hass.http = SimpleNamespace(async_register_static_paths=AsyncMock())
    with (
        patch("custom_components.birdweather.async_get_integration", return_value=SimpleNamespace(version="0.5.0")),
        patch("custom_components.birdweather.add_extra_js_url") as inject,
    ):
        assert await async_setup(hass, {})

    paths = hass.http.async_register_static_paths.call_args.args[0]
    assert {path.url_path for path in paths} == {
        "/birdweather/birdweather-bird-card.js",
        "/birdweather/birdweather-bird-list-card.js",
        "/birdweather/birdweather-wildlife.js",
    }
    assert all(Path(path.path).is_file() for path in paths)
    assert {call.args[1] for call in inject.call_args_list} == {
        "/birdweather/birdweather-bird-card.js?v=0.5.0",
        "/birdweather/birdweather-bird-list-card.js?v=0.5.0",
    }
