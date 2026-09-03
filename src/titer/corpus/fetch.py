"""Fetch the SEC Insider Transactions Data Sets.

Two rules here are not style preferences:

1. **Quarterly links are scraped from the landing page, never generated.**
   A generated recent-quarter filename returns 404 while the landing page
   advertises that quarter, so a generator truncates the corpus at a boundary
   nobody would notice. See docs/HANDOFF.md.

2. **A declared User-Agent is mandatory and the request rate is deliberately
   far below the limit.** SEC states 10 requests/second and blocks the source
   IP on excess, for the whole IP, across every sec.gov host. The corpus needs
   roughly 80 requests in total, so there is nothing to gain by going fast.
"""
from __future__ import annotations

import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

LANDING = (
    "https://www.sec.gov/data-research/sec-markets-data/"
    "insider-transactions-data-sets"
)
BASE = "https://www.sec.gov"
_LINK = re.compile(
    r"/files/structureddata/data/insider-transactions-data-sets/"
    r"(\d{4})q([1-4])_form345\.zip",
    re.I,
)
# Deliberately ~0.67 req/s against a stated 10 req/s limit. SEC's real
# behaviour is burst-sensitive well below the documented ceiling.
MIN_INTERVAL_S = 1.5


class SecAccessError(RuntimeError):
    """Raised with the actionable cause rather than a bare HTTP code."""


def user_agent() -> str:
    """SEC requires a declared UA with a contact address.

    Read from the environment so no address is ever committed to this
    repository - the privacy gate in scripts/validate.py rejects
    email-shaped strings in tracked files.
    """
    ua = os.environ.get("TITER_SEC_UA", "").strip()
    if not ua:
        raise SecAccessError(
            "TITER_SEC_UA is unset. SEC blocks undeclared automated access. "
            "Export a contact string, e.g.:\n"
            "  export TITER_SEC_UA='titer-research <handle>@users.noreply.github.com'"
        )
    return ua


@dataclass(frozen=True, slots=True)
class Quarter:
    year: int
    quarter: int
    url: str

    @property
    def key(self) -> str:
        return f"{self.year}q{self.quarter}"

    def __lt__(self, other: "Quarter") -> bool:
        return (self.year, self.quarter) < (other.year, other.quarter)


_last_request_at = 0.0


def _get(url: str, timeout: int = 60) -> bytes:
    global _last_request_at
    wait = MIN_INTERVAL_S - (time.monotonic() - _last_request_at)
    if wait > 0:
        time.sleep(wait)
    req = urllib.request.Request(url, headers={
        "User-Agent": user_agent(),
        "Accept-Encoding": "gzip, deflate",
        "Host": url.split("/")[2],
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        if e.code == 403:
            raise SecAccessError(
                f"SEC returned 403 for {url}.\n\n"
                "Diagnosed 2026-09-03: this is BURST throttling keyed on "
                "(source IP, User-Agent), not a persistent IP ban, and SEC's 403 "
                "page is titled 'Request Rate Threshold Exceeded' regardless of "
                "cause - do not diagnose from the page title. A few requests "
                "sent back-to-back trigger it; the same request spaced a couple "
                "of seconds apart succeeds.\n\n"
                "Checks, in order:\n"
                "  1. Is TITER_SEC_UA of the form 'Company Name contact@domain'? "
                "An address containing '+' has been observed failing.\n"
                "  2. Wait ~30s and retry ONCE. Do not loop - each retry "
                "re-triggers the throttle.\n"
                "  3. MIN_INTERVAL_S is the guard; raise it rather than adding "
                "retries."
            ) from e
        raise
    finally:
        _last_request_at = time.monotonic()


def discover_quarters() -> list[Quarter]:
    """Scrape the landing page. Never generate filenames."""
    html = _get(LANDING).decode("utf-8", errors="replace")
    seen: dict[str, Quarter] = {}
    for m in _LINK.finditer(html):
        year, q = int(m.group(1)), int(m.group(2))
        url = BASE + m.group(0)
        seen.setdefault(f"{year}q{q}", Quarter(year, q, url))
    if not seen:
        raise SecAccessError(
            "No quarterly links found on the landing page. Either the page layout "
            "changed or the response was an error page. Do NOT fall back to "
            "generating filenames - that silently truncates the corpus."
        )
    return sorted(seen.values())


def download(q: Quarter, dest_dir: Path) -> Path:
    """Download one quarter, skipping if already present."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    out = dest_dir / f"{q.key}_form345.zip"
    if out.exists() and out.stat().st_size > 0:
        return out
    data = _get(q.url)
    tmp = out.with_suffix(".zip.part")
    tmp.write_bytes(data)
    tmp.replace(out)
    return out
