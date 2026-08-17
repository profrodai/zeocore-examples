"""
Plain-Python cleaning helpers, ported from agency-data-onboarding-kit's own
scripts/utils.py (same repo this app rebuilds -- see the app README for the
link). These stay untyped-in/untyped-out on purpose, matching the original;
the zeocore layer (small_tools.py, pipeline_tools.py) wraps them with typed
pydantic request/response models and CapabilityResult returns. This module
is the "business logic" ring; the tool classes are the doctrine ring.
"""

from __future__ import annotations

import re

COUNTRY_MAP = {
    "usa": "United States",
    "us": "United States",
    "united states": "United States",
    "u.s.": "United States",
    "u.s.a.": "United States",
    "uk": "United Kingdom",
    "gb": "United Kingdom",
    "united kingdom": "United Kingdom",
    "u.k.": "United Kingdom",
    "great britain": "United Kingdom",
}


def extract_domain(url: str | None) -> str | None:
    """Extract a clean domain from a website URL or email-style string."""
    if not url or url == "":
        return None

    domain = str(url).lower().strip()
    domain = domain.replace("http://", "")
    domain = domain.replace("https://", "")
    domain = domain.replace("www.", "")
    domain = domain.split("/")[0]
    domain = domain.rstrip(".")

    if "." not in domain:
        return None

    return domain


def normalize_country(country: str | None) -> str | None:
    """Normalize a country name/code to a standard display form."""
    if not country or country == "":
        return None

    clean = str(country).strip().lower()

    if clean in COUNTRY_MAP:
        return COUNTRY_MAP[clean]

    return country.strip().title()


def clean_phone(phone: str | None) -> str | None:
    """Clean a phone number to digits-only, preserving a leading +."""
    if not phone or phone == "":
        return None

    phone_str = str(phone).strip()
    has_plus = phone_str.startswith("+")
    digits_only = re.sub(r"[^0-9]", "", phone_str)

    if not digits_only:
        return None

    if has_plus:
        return f"+{digits_only}"

    return digits_only


def clean_linkedin_url(url: str | None) -> str | None:
    """Standardize a LinkedIn profile URL to https://linkedin.com/... form."""
    if not url or url == "":
        return None

    clean_url = str(url).lower().strip()
    clean_url = clean_url.replace("https://", "")
    clean_url = clean_url.replace("http://", "")
    clean_url = clean_url.replace("www.", "")
    clean_url = clean_url.rstrip("/")

    if not clean_url.startswith("linkedin.com"):
        return None

    return f"https://{clean_url}"


def clean_email(email: str | None) -> str | None:
    """Lowercase/strip an email address; return None if obviously invalid."""
    if not email or email == "":
        return None

    clean = str(email).lower().strip()

    if "@" not in clean:
        return None

    return clean


def is_valid_email(email: str | None) -> bool:
    """True if email looks real (not empty, not a generic/test address)."""
    if not email:
        return False

    email_lower = email.lower()

    if "@" not in email_lower:
        return False

    invalid_prefixes = ["test@", "example@", "info@", "admin@", "noreply@"]
    for prefix in invalid_prefixes:
        if email_lower.startswith(prefix):
            return False

    invalid_domains = ["example.com", "test.com", "localhost"]
    domain = email_lower.split("@")[-1]
    if domain in invalid_domains:
        return False

    return True


def calculate_completeness_score(row_dict: dict, fields: list) -> int:
    """Count non-null/non-empty/non-N/A fields in row_dict among fields."""
    score = 0
    for field in fields:
        value = row_dict.get(field)
        if value and value != "" and value != "N/A":
            score += 1
    return score


def normalize_column_name(col: str) -> str:
    """Normalize a CSV header to snake_case."""
    clean = col.strip().lower().replace(" ", "_")
    while "__" in clean:
        clean = clean.replace("__", "_")
    return clean
