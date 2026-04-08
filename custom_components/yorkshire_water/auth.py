"""Yorkshire Water OAuth2 PKCE authentication."""
from __future__ import annotations

import base64
import hashlib
import logging
import os
import re
import urllib.parse

import aiohttp

from .const import AUTHORIZE_URL, TOKEN_URL, CLIENT_ID, REDIRECT_URI, SCOPES

_LOGGER = logging.getLogger(__name__)


def _extract_csrf(html: str) -> str:
    """Extract __RequestVerificationToken value from login page HTML."""
    m = re.search(r'<input[^>]+name="__RequestVerificationToken"[^>]+value="([^"]+)"', html)
    if not m:
        m = re.search(r'<input[^>]+value="([^"]+)"[^>]+name="__RequestVerificationToken"', html)
    if m:
        return m.group(1)
    idx = html.find("__RequestVerificationToken")
    if idx == -1:
        return ""
    chunk = html[max(0, idx - 400):idx + 400]
    m = re.search(r'value=.([A-Za-z0-9_\\\\-]{20,})', chunk)
    if m:
        return m.group(1)
    return ""


def _generate_pkce_pair() -> tuple[str, str]:
    code_verifier = base64.urlsafe_b64encode(os.urandom(40)).rstrip(b"=").decode()
    digest = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return code_verifier, code_challenge


def _generate_state() -> str:
    return base64.urlsafe_b64encode(os.urandom(16)).rstrip(b"=").decode()


class YorkshireWaterAuth:
    def __init__(self) -> None:
        self._session: aiohttp.ClientSession | None = None
        self.access_token: str | None = None
        self.refresh_token: str | None = None

    def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                cookie_jar=aiohttp.CookieJar(),
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
                    "Accept-Language": "en-GB,en;q=0.9",
                },
            )
        return self._session

    async def async_login(self, email: str, password: str) -> dict:
        """Full PKCE login flow. Returns token dict."""
        session = self._get_session()
        code_verifier, code_challenge = _generate_pkce_pair()
        state = _generate_state()

        params = {
            "client_id": CLIENT_ID, "redirect_uri": REDIRECT_URI,
            "response_type": "code", "scope": SCOPES, "state": state,
            "code_challenge": code_challenge, "code_challenge_method": "S256",
            "response_mode": "query",
        }
        auth_url = AUTHORIZE_URL + "?" + urllib.parse.urlencode(params)

        # Step 1: GET authorize — follow redirects to land on login page
        async with session.get(auth_url, allow_redirects=True) as resp:
            login_url = str(resp.url)
            login_html = await resp.text()

        csrf = _extract_csrf(login_html)
        if not csrf:
            raise PermissionError("Could not extract CSRF token from login page")

        # Step 2: POST credentials
        payload = {
            "Email": email,
            "Password": password,
            "g-recaptcha-response": "",
            "RedirectUrl": "https://my.yorkshirewater.com/account",
            "__RequestVerificationToken": csrf,
        }
        async with session.post(login_url, data=payload, allow_redirects=False) as resp:
            location = resp.headers.get("Location", "")

        if location and not location.startswith("http"):
            location = urllib.parse.urljoin(login_url, location)

        if not location:
            raise PermissionError("No redirect after login POST — check credentials")
        if "login.yorkshirewater.com" in location and "login=true" not in location:
            raise PermissionError("Login failed — invalid credentials")

        # Step 3: follow login redirect to establish session cookies
        async with session.get(location, allow_redirects=True) as resp:
            pass

        # Step 4: re-hit authorize with authenticated session to get code
        async with session.get(auth_url, allow_redirects=True) as resp:
            final_url = str(resp.url)

        if "code" not in final_url:
            raise PermissionError("Authentication failed — no authorisation code returned")

        # Step 5: extract auth code from callback URL
        parsed = urllib.parse.urlparse(final_url)
        qs = urllib.parse.parse_qs(parsed.query)

        if "code" not in qs:
            raise PermissionError("Authentication failed — no authorisation code in callback")

        auth_code = qs["code"][0]

        # Step 6: exchange code for tokens
        token_data = {
            "grant_type": "authorization_code", "client_id": CLIENT_ID,
            "code": auth_code, "redirect_uri": REDIRECT_URI,
            "code_verifier": code_verifier,
        }
        async with session.post(
            TOKEN_URL, data=token_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        ) as resp:
            if resp.status != 200:
                body = await resp.text()
                raise PermissionError(f"Token exchange failed ({resp.status})")
            tokens = await resp.json()

        self.access_token = tokens.get("access_token")
        self.refresh_token = tokens.get("refresh_token")
        _LOGGER.info("Yorkshire Water authentication successful")
        return tokens

    async def async_refresh(self) -> dict:
        """Refresh access token using refresh token."""
        if not self.refresh_token:
            raise PermissionError("No refresh token available")
        session = self._get_session()
        data = {
            "grant_type": "refresh_token",
            "client_id": CLIENT_ID,
            "refresh_token": self.refresh_token,
        }
        async with session.post(
            TOKEN_URL, data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        ) as resp:
            if resp.status != 200:
                _LOGGER.warning("Yorkshire Water token refresh failed (status %d)", resp.status)
                raise PermissionError("Token refresh failed")
            tokens = await resp.json()
        self.access_token = tokens.get("access_token")
        self.refresh_token = tokens.get("refresh_token", self.refresh_token)
        return tokens

    async def async_close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()