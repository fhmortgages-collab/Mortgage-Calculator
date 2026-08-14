import re
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

OSFI_MQR_URL = (
    "https://www.osfi-bsif.gc.ca/en/supervision/financial-institutions/"
    "banks/minimum-qualifying-rate-uninsured-mortgages"
)

DEFAULT_BUFFER_PCT = 2.00
DEFAULT_FLOOR_PCT = 5.25


def get_osfi_minimum_qualifying_rate():
    """
    Fetch OSFI's current uninsured-mortgage qualifying-rate rule.

    Returns a dictionary with the buffer, floor, source status, and timestamp.
    Uses known defaults only if the OSFI website is unavailable or its wording
    cannot be parsed.
    """
    result = {
        "buffer_pct": DEFAULT_BUFFER_PCT,
        "floor_pct": DEFAULT_FLOOR_PCT,
        "source_url": OSFI_MQR_URL,
        "source_status": "Fallback values in use",
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "error": None,
    }

    try:
        response = requests.get(
            OSFI_MQR_URL,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (compatible; MortgageStressTestApp/1.0)"
                )
            },
            timeout=15,
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        page_text = soup.get_text(" ", strip=True)
        normalized_text = re.sub(r"\s+", " ", page_text).lower()

        match = re.search(
            r"greater\s+of\s+the\s+mortgage\s+contract\s+rate\s+plus\s+"
            r"(\d+(?:\.\d+)?)\s*%\s+or\s+(\d+(?:\.\d+)?)\s*%",
            normalized_text,
        )

        if match:
            result["buffer_pct"] = float(match.group(1))
            result["floor_pct"] = float(match.group(2))
            result["source_status"] = "Live OSFI guideline retrieved"


        Add live OSFI stress test rate helper
        else:
            result["source_status"] = (
                "OSFI page retrieved but could not parse rate wording; "
                "fallback values are in use"
            )

    except requests.RequestException as exc:
        result["error"] = str(exc)

    return result


def calculate_qualifying_rate(contract_rate_pct):
    """
    Returns the current OSFI qualifying rate:
    max(contract rate + OSFI buffer, OSFI floor).
    """
    osfi = get_osfi_minimum_qualifying_rate()

    contract_plus_buffer_pct = contract_rate_pct + osfi["buffer_pct"]
    qualifying_rate_pct = max(contract_plus_buffer_pct, osfi["floor_pct"])

    return {
        **osfi,
        "contract_rate_pct": contract_rate_pct,
        "contract_plus_buffer_pct": contract_plus_buffer_pct,
        "qualifying_rate_pct": qualifying_rate_pct,
    }
