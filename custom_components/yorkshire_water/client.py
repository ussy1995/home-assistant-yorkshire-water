"""Yorkshire Water API client."""
from __future__ import annotations

import logging
from datetime import date

import aiohttp
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant

from .auth import YorkshireWaterAuth
from .const import (
    API_DAILY,
    API_YOUR_USAGE,
    API_PROPERTY,
    CONF_METER_REFERENCE,
    CONF_ACCOUNT_REFERENCE,
    PORTAL_BASE,
)

_LOGGER = logging.getLogger(__name__)

API_METER_DETAILS = f"{PORTAL_BASE}/api/account/smartmeter/meter-details"


class YorkshireWaterAuthError(Exception):
    pass


class YorkshireWaterClient:
    def __init__(self, hass: HomeAssistant, config: dict) -> None:
        self._hass = hass
        self._email = config[CONF_EMAIL]
        self._password = config[CONF_PASSWORD]
        self._account_reference = config[CONF_ACCOUNT_REFERENCE]
        self._meter_reference = config.get(CONF_METER_REFERENCE)
        self._auth = YorkshireWaterAuth()
        self._session: aiohttp.ClientSession | None = None

    def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def _ensure_token(self) -> None:
        """Login if no token, then ensure meter_reference is known."""
        if not self._auth.access_token:
            try:
                await self._auth.async_login(self._email, self._password)
            except PermissionError as err:
                raise YorkshireWaterAuthError(str(err)) from err

        if not self._meter_reference:
            await self._fetch_meter_reference()

    async def _fetch_meter_reference(self) -> None:
        """Call meter-details with account reference to get meter reference."""
        try:
            data = await self._get(
                API_METER_DETAILS,
                {"accountReference": self._account_reference},
            )
            self._meter_reference = data.get("meterReference")
        except Exception as err:
            _LOGGER.warning("Could not retrieve meter reference: %s", err)

    async def _get(self, url: str, params: dict) -> dict | list:
        """Authenticated GET with single token refresh retry on 401."""
        session = self._get_session()
        headers = {
            "Authorization": f"Bearer {self._auth.access_token}",
            "Accept": "application/json",
        }
        async with session.get(url, headers=headers, params=params) as resp:
            if resp.status == 401:
                try:
                    await self._auth.async_refresh()
                except PermissionError:
                    self._auth.access_token = None
                    await self._ensure_token()
                headers["Authorization"] = f"Bearer {self._auth.access_token}"
                async with session.get(url, headers=headers, params=params) as r2:
                    if r2.status != 200:
                        raise ConnectionError(f"API error {r2.status}")
                    return await r2.json()
            if resp.status != 200:
                raise ConnectionError(f"API error {resp.status}")
            return await resp.json()

    async def async_get_daily_consumption(
        self, start: date, end: date, time_period: int = 1
    ) -> dict:
        """Fetch daily consumption for a date range.

        time_period=1 for month view, 0 for week view.
        """
        await self._ensure_token()
        params = {
            "meterReference": self._meter_reference,
            "startDate": start.isoformat(),
            "endDate": end.isoformat(),
            "timePeriod": time_period,
        }
        return await self._get(API_DAILY, params)

    async def async_get_your_usage(self) -> list:
        """Fetch monthly summary — [0] this month, [1] last month."""
        await self._ensure_token()
        params = {"meterReference": self._meter_reference}
        return await self._get(API_YOUR_USAGE, params)

    async def async_close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
        await self._auth.async_close()