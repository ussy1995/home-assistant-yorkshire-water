# Yorkshire Water Smart Meter
### Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-cyan.svg)](https://hacs.xyz)
[![HA Version](https://img.shields.io/badge/Home%20Assistant-2024.6%2B-blue.svg)](https://www.home-assistant.io)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

> ⚠️ **Unofficial integration.** Not affiliated with, endorsed by, or supported by Yorkshire Water Services Limited.

Bring your Yorkshire Water smart meter data directly into Home Assistant. Monitor daily usage, track monthly spend, and set automations based on your water consumption — all without leaving HA.

---

## Features

- 📊 **12 sensors** covering last reading, this month, last month, weekly, and daily averages
- 🚨 **3 binary sensors** for continuous flow alarm, estimated data, and missing data flags
- 💷 **All costs include sewerage** — no need to manually calculate
- 🔄 **Automatic refresh** every 6 hours
- 🏠 Built for Home Assistant Energy dashboard compatibility

---

## Requirements

- Home Assistant 2024.6 or later
- A registered account at [my.yorkshirewater.com](https://my.yorkshirewater.com)
- A Yorkshire Water smart meter

---

## Installation via HACS

1. Open **HACS** → **Integrations** → click the **3 dots** (top right) → **Custom repositories**
2. Enter URL: `https://github.com/ussy1995/home-assistant-yorkshire-water`
3. Set Category to **Integration** → click **Add**
4. Search for **"Yorkshire Water"** → click **Download** → **Restart Home Assistant**

---

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **Yorkshire Water**
3. Enter your credentials:

| Field | Description |
|---|---|
| **Email** | Your my.yorkshirewater.com login email |
| **Password** | Your my.yorkshirewater.com password |
| **Account Reference** | Your customer account reference number, printed on your bill — numbers only, no spaces, no letters (e.g. `541729360000000`) |

> 💡 Your account reference can be found on any Yorkshire Water bill or letter.

---

## Entities

### Sensors

| Entity | Description | Unit |
|---|---|---|
| `sensor.yorkshire_water_last_reading_date` | Date of the most recent meter reading | — |
| `sensor.yorkshire_water_last_reading_litres` | Litres consumed on last reading day | L |
| `sensor.yorkshire_water_last_reading_cost` | Cost on last reading day (inc. sewerage) | GBP |
| `sensor.yorkshire_water_this_month_litres` | Total litres this calendar month | L |
| `sensor.yorkshire_water_this_month_cost` | Total cost this calendar month (inc. sewerage) | GBP |
| `sensor.yorkshire_water_last_month_litres` | Total litres last calendar month | L |
| `sensor.yorkshire_water_last_month_cost` | Total cost last calendar month (inc. sewerage) | GBP |
| `sensor.yorkshire_water_weekly_litres` | Total litres over last 7 complete days | L |
| `sensor.yorkshire_water_weekly_cost` | Total cost over last 7 complete days | GBP |
| `sensor.yorkshire_water_weekly_daily_average_litres` | Daily average litres over last 7 complete days | L |
| `sensor.yorkshire_water_daily_average_litres_mtd` | Daily average litres month-to-date | L |
| `sensor.yorkshire_water_daily_average_cost_mtd` | Daily average cost month-to-date | GBP |

### Binary Sensors

| Entity | Description | Triggers when... |
|---|---|---|
| `binary_sensor.yorkshire_water_continuous_flow_alarm` | Continuous flow detected | Water flowing without interruption (possible leak) |
| `binary_sensor.yorkshire_water_estimated_consumption` | Consumption data is estimated | Yorkshire Water has estimated rather than read your meter |
| `binary_sensor.yorkshire_water_missing_consumption` | Consumption data is missing | No reading data available for one or more days |

---

## Example Automations

**Alert if daily usage is unusually high:**
```yaml
automation:
  - alias: "High water usage alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.yorkshire_water_last_reading_litres
        above: 1000
    action:
      - action: notify.mobile_app
        data:
          message: "⚠️ High water usage yesterday: {{ states('sensor.yorkshire_water_last_reading_litres') }}L"
```

**Alert on continuous flow alarm:**
```yaml
automation:
  - alias: "Yorkshire Water leak alert"
    trigger:
      - platform: state
        entity_id: binary_sensor.yorkshire_water_continuous_flow_alarm
        to: "on"
    action:
      - action: notify.mobile_app
        data:
          message: "🚨 Yorkshire Water: Continuous flow alarm triggered — possible leak!"
```

---

## Notes

- Meter readings typically lag **1–2 days** behind real time — this is a Yorkshire Water platform limitation, not an integration bug
- All cost sensors include **both water and sewerage charges**
- Weekly sensors use the last **7 complete days** of data, not a fixed Mon–Sun week
- Monthly sensors reflect the periods returned by the Yorkshire Water API — this is broadly aligned to the calendar month but may vary
- The meter reference number is discovered automatically during setup — you do not need to find or enter it manually

---
## Diagnostics & Logging

To enable debug logging for troubleshooting, add the following to your `configuration.yaml`:

```yaml
logger:
  default: warning
  logs:
    custom_components.yorkshire_water: debug
```

This will log a summary after each successful data fetch. Disable it again once your issue is resolved.
---
## Contributing

Contributions are welcome and encouraged! Whether it's a bug fix, a new feature, or an improvement to the docs — all PRs are appreciated.

Please be respectful and constructive. All contributors will be credited below.

### Contributors

<!-- ALL-CONTRIBUTORS-LIST:START -->
| Contributor | Role |
|---|---|
| [@ussy1995](https://github.com/ussy1995) | Creator & maintainer |
<!-- ALL-CONTRIBUTORS-LIST:END -->

---

## Disclaimer

This integration is an independent, community-built project. It is not affiliated with, endorsed by, or officially supported by Yorkshire Water Services Limited. Use at your own risk.

---

## License

[GNU General Public License v3.0](LICENSE) — you are free to use, modify, and distribute this project, but any derivative work must also remain open source under the same licence. You may not copy this project and republish it as your own closed-source or commercial product.
