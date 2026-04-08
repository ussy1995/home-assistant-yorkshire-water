"""Constants for Yorkshire Water integration."""
from __future__ import annotations

DOMAIN = "yorkshire_water"
CONF_METER_REFERENCE = "meter_reference"
CONF_ACCOUNT_REFERENCE = "account_reference"

# How often the coordinator polls the Yorkshire Water API
SCAN_INTERVAL_HOURS = 6

AUTH_BASE      = "https://login.yorkshirewater.com"
AUTHORIZE_URL  = f"{AUTH_BASE}/connect/authorize"
TOKEN_URL      = f"{AUTH_BASE}/connect/token"
PORTAL_BASE    = "https://my.yorkshirewater.com"
API_BASE       = f"{PORTAL_BASE}/api/account/smartmeter"
API_ACCOUNT_BASE = f"{PORTAL_BASE}/api/account"

API_DAILY      = f"{API_BASE}/daily-consumption"
API_YOUR_USAGE = f"{API_BASE}/your-usage"
API_PROPERTY   = f"{API_ACCOUNT_BASE}/properties/detail"

CLIENT_ID    = "css-onlineaccount-fe"
REDIRECT_URI = f"{PORTAL_BASE}/account/callback/response"
SCOPES       = "openid user-names css-onlineaccount-api css-registration-api"