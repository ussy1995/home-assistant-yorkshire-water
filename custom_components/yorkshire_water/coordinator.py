"""Data update coordinator for Yorkshire Water."""
from __future__ import annotations

import logging
from datetime import date, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import YorkshireWaterClient, YorkshireWaterAuthError
from .const import DOMAIN, SCAN_INTERVAL_HOURS

_LOGGER = logging.getLogger(__name__)


def _f(value: object) -> float:
    """Coerce string or numeric API value to float, default 0."""
    try:
        return float(value) if value is not None else 0.0
    except (ValueError, TypeError):
        return 0.0


class YorkshireWaterDataUpdateCoordinator(DataUpdateCoordinator[dict]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.client = YorkshireWaterClient(hass, entry.data)
        super().__init__(
            hass, _LOGGER, name=DOMAIN,
            update_interval=timedelta(hours=SCAN_INTERVAL_HOURS),
        )

    async def _async_update_data(self) -> dict:
        try:
            return await self._fetch()
        except YorkshireWaterAuthError as err:
            raise UpdateFailed("Yorkshire Water authentication failed") from err
        except ConnectionError as err:
            raise UpdateFailed("Yorkshire Water connection error") from err
        except Exception as err:
            raise UpdateFailed("Yorkshire Water unexpected error") from err

    async def _fetch(self) -> dict:
        today = date.today()

        # ── Daily consumption (month-to-date) ─────────────────────────────────
        month_start = today.replace(day=1)
        daily_resp = await self.client.async_get_daily_consumption(
            month_start, today, time_period=1
        )
        daily_list = sorted(
            daily_resp.get("dailyUsageData") or [],
            key=lambda x: x["date"],
        )

        # Last complete day = most recent non-missing entry strictly before today
        last_complete = next(
            (
                d for d in reversed(daily_list)
                if not d.get("isMissingConsumption", False)
                and d["date"] < today.isoformat()
            ),
            None,
        )

        # ── Last month daily data (for weekly rollup on Mondays) ───────────────
        last_month_start = (month_start - timedelta(days=1)).replace(day=1)
        last_month_end   = month_start - timedelta(days=1)

        if today.weekday() == 0:  # Monday only
            prev_daily_resp = await self.client.async_get_daily_consumption(
                last_month_start, last_month_end, time_period=1
            )
            prev_daily_list = sorted(
                prev_daily_resp.get("dailyUsageData") or [],
                key=lambda x: x["date"],
            )
        else:
            prev_daily_list = []

        all_daily = prev_daily_list + daily_list

        # ── Monthly summary (your-usage) ───────────────────────────────────────
        your_usage = await self.client.async_get_your_usage()
        this_month = your_usage[0] if len(your_usage) > 0 else {}
        last_month = your_usage[1] if len(your_usage) > 1 else {}

        # ── Weekly rollup (last 7 complete days) ──────────────────────────────
        complete_days = [
            d for d in all_daily
            if not d.get("isMissingConsumption", False)
            and d["date"] < today.isoformat()
        ]
        last_7 = complete_days[-7:] if len(complete_days) >= 7 else complete_days
        weekly_litres = sum(_f(d.get("totalConsumptionLitres")) for d in last_7)
        weekly_cost   = sum(_f(d.get("totalCostIncludingSewerage")) for d in last_7)
        weekly_days   = len(last_7)
        weekly_daily_avg_litres = round(weekly_litres / weekly_days, 1) if weekly_days else None

        _LOGGER.debug(
            "Yorkshire Water fetch complete — last_complete=%s, weekly_days=%d, "
            "this_month_litres=%s",
            last_complete.get("date") if last_complete else "None",
            weekly_days,
            this_month.get("totalConsumptionLitres"),
        )

        return {
            # ── Last complete day ──────────────────────────────────────────────
            "last_complete_day": last_complete,

            # ── MTD averages ──────────────────────────────────────────────────
            "mtd_daily_litres_average": daily_resp.get("dailyLitresAverage"),
            "mtd_daily_cost_average":   daily_resp.get("dailyCostAverageForYear"),

            # ── Weekly (last 7 complete days) ─────────────────────────────────
            "weekly_litres":           round(weekly_litres, 1),
            "weekly_cost":             round(weekly_cost, 2),
            "weekly_daily_avg_litres": weekly_daily_avg_litres,
            "weekly_days_counted":     weekly_days,

            # ── This month ────────────────────────────────────────────────────
            "this_month_litres":            this_month.get("totalConsumptionLitres"),
            "this_month_water_cost":        this_month.get("standardTariffCleanWaterCost"),
            "this_month_sewerage_cost":     this_month.get("standardTariffSewerageCost"),
            "this_month_cost_inc_sewerage": this_month.get("totalCostIncludingSewerage"),
            "this_month_estimated_days":    this_month.get("estimatedDayCount"),
            "this_month_missing_days":      this_month.get("missingDayCount"),

            # ── Last month ────────────────────────────────────────────────────
            "last_month_litres":            last_month.get("totalConsumptionLitres"),
            "last_month_water_cost":        last_month.get("standardTariffCleanWaterCost"),
            "last_month_sewerage_cost":     last_month.get("standardTariffSewerageCost"),
            "last_month_cost_inc_sewerage": last_month.get("totalCostIncludingSewerage"),
            "last_month_estimated_days":    last_month.get("estimatedDayCount"),

            # ── Raw lists (binary sensors) ────────────────────────────────────
            "daily_list": daily_list,
            "all_daily":  all_daily,
        }