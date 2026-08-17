"""
Three small, single-purpose zeocore tools, each wrapping one of
agency-data-onboarding-kit's own reusable utility functions
(scripts/utils.py) as a typed BaseZeoTool.

This is the "many small typed tools" shape zeocore's own README pitches
directly (see the quick-start GreetTool example) -- proving it against real
validation logic, not a toy, is the point of these three.
"""

from __future__ import annotations

from pydantic import BaseModel
from zeo_core.contracts import CapabilityResult
from zeo_core.tools import BaseZeoTool, ToolContext

from data_cleaning._utils import (
    clean_email,
    extract_domain,
    is_valid_email,
    normalize_country,
)


class CleanEmailRequest(BaseModel):
    email: str | None = None


class CleanEmailResponse(BaseModel):
    cleaned_email: str | None
    is_valid: bool


class CleanEmailTool(BaseZeoTool):
    """Lowercase/validate a single email address."""

    name = "clean_email"
    version = "1.0.0"

    def run(
        self, request: CleanEmailRequest, ctx: ToolContext
    ) -> CapabilityResult[CleanEmailResponse]:
        cleaned = clean_email(request.email)
        valid = is_valid_email(cleaned) if cleaned else False
        return CapabilityResult.ok(
            data=CleanEmailResponse(cleaned_email=cleaned, is_valid=valid),
            msg="Email cleaned",
            metadata={"tool": f"{self.name} v{self.version}"},
        )


class NormalizeCountryRequest(BaseModel):
    country: str | None = None


class NormalizeCountryResponse(BaseModel):
    normalized_country: str | None


class NormalizeCountryTool(BaseZeoTool):
    """Normalize a country name/code (e.g. 'UK', 'usa') to a standard form."""

    name = "normalize_country"
    version = "1.0.0"

    def run(
        self, request: NormalizeCountryRequest, ctx: ToolContext
    ) -> CapabilityResult[NormalizeCountryResponse]:
        normalized = normalize_country(request.country)
        return CapabilityResult.ok(
            data=NormalizeCountryResponse(normalized_country=normalized),
            msg="Country normalized",
            metadata={"tool": f"{self.name} v{self.version}"},
        )


class ExtractDomainRequest(BaseModel):
    url: str | None = None


class ExtractDomainResponse(BaseModel):
    domain: str | None


class ExtractDomainTool(BaseZeoTool):
    """Extract a clean bare domain from a website URL or email-shaped string."""

    name = "extract_domain"
    version = "1.0.0"

    def run(
        self, request: ExtractDomainRequest, ctx: ToolContext
    ) -> CapabilityResult[ExtractDomainResponse]:
        domain = extract_domain(request.url)
        return CapabilityResult.ok(
            data=ExtractDomainResponse(domain=domain),
            msg="Domain extracted",
            metadata={"tool": f"{self.name} v{self.version}"},
        )
