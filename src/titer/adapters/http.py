"""Real HTTP transports. The only code in the repository that spends money.

Every transport is explicit about three things, because each has burned this
project once already:

* **Credentials come from the environment, never from a tracked file.**
* **Nothing retries on its own.** A retry loop against a burst-throttled API
  turns one 403 into a ban; SEC taught that lesson.
* **The caller owns the budget.** A transport reports what a call cost; it does
  not decide whether the call was affordable.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

CLIENT_UA = "titer/0.1 (+https://github.com/caiotheodoro/titer)"

# Per-provider request spacing, from each provider's PUBLISHED limit - not a
# guess, and not one global default. Ploid's Free plan is 10 requests/minute;
# firing at the old global 1.0s (60/min) drew 14 straight 429s and wasted a run
# on a grant denominated in credits. The limit was already written down in
# docs/HANDOFF.md and simply never reached the transport.
MIN_INTERVAL_S = 1.0
PROVIDER_INTERVAL_S = {
    "ploid": 7.0,   # published 10/min on Free; 7s leaves margin
    "exa": 1.0,     # published 10 QPS on /search
}


class ProviderHTTPError(RuntimeError):
    def __init__(self, provider: str, status: int, body: str, url: str):
        self.provider, self.status, self.body, self.url = provider, status, body, url
        hint = {
            401: "check the API key in .env",
            403: "key lacks scope, or the account is inactive",
            422: "unsupported filter or category for this endpoint",
            429: "rate limited - respect Retry-After, do NOT loop",
            503: "provider retrieval failure; it fails closed and returns no partial results",
        }.get(status, "")
        super().__init__(f"{provider} {status} for {url}: {body[:300]}"
                         + (f"\n  hint: {hint}" if hint else ""))


@dataclass
class HTTPTransport:
    """One provider's HTTP surface. Callable as `transport(method, path, payload)`."""

    provider: str
    base_url: str
    headers: dict[str, str] = field(default_factory=dict)
    timeout: int = 60
    calls: int = 0
    _last: float = 0.0

    def __call__(self, method: str, path: str, payload: dict[str, Any]) -> dict:
        interval = PROVIDER_INTERVAL_S.get(self.provider, MIN_INTERVAL_S)
        wait = interval - (time.monotonic() - self._last)
        if wait > 0:
            time.sleep(wait)
        url = self.base_url.rstrip("/") + path
        data = None
        if method.upper() == "GET":
            if payload:
                from urllib.parse import urlencode
                url = f"{url}?{urlencode(payload)}"
        else:
            data = json.dumps(payload).encode()
        req = urllib.request.Request(url, data=data, method=method.upper(),
                                     headers={"Content-Type": "application/json",
                                              "Accept": "application/json",
                                              # urllib's default UA is blocked by
                                              # Cloudflare (error 1010, "blocked
                                              # based on your browser signature").
                                              # We identify honestly as this client
                                              # rather than impersonating a browser.
                                              "User-Agent": CLIENT_UA,
                                              **self.headers})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                self.calls += 1
                return json.loads(r.read().decode() or "{}")
        except urllib.error.HTTPError as e:
            raise ProviderHTTPError(self.provider, e.code,
                                    e.read().decode(errors="replace"), url) from e
        finally:
            self._last = time.monotonic()


def ploid_transport() -> HTTPTransport:
    key = os.environ.get("PLOID_API_KEY", "").strip()
    if not key:
        raise RuntimeError("PLOID_API_KEY is unset; put it in .env (gitignored)")
    return HTTPTransport("ploid", "https://api.ploid.com",
                         {"Authorization": f"Bearer {key}"})


def exa_transport() -> HTTPTransport:
    key = os.environ.get("EXA_API_KEY", "").strip()
    if not key:
        raise RuntimeError("EXA_API_KEY is unset; put it in .env (gitignored)")
    return HTTPTransport("exa", "https://api.exa.ai", {"x-api-key": key})
