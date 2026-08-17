"""
The two pipeline tools rebuilding agency-data-onboarding-kit's own
scripts/clean_contacts.py and scripts/clean_accounts.py as zeocore
BaseZeoTool subclasses: typed pydantic requests, real polars-backed cleaning
logic (same steps as the original: normalize columns, clean fields, filter
invalid rows, dedupe by completeness score), and a typed CapabilityResult
carrying the same stats the original's bare dict return carried.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl
from pydantic import BaseModel, Field
from zeo_core.contracts import CapabilityResult
from zeo_core.tools import BaseZeoTool, ToolContext

from data_cleaning._utils import (
    clean_linkedin_url,
    clean_phone,
    extract_domain,
    is_valid_email,
    normalize_column_name,
    normalize_country,
)


class CleaningStats(BaseModel):
    """Typed replacement for the original's bare `dict` stats return."""

    original_count: int
    invalid_filtered: int
    duplicates_removed: int
    final_count: int
    data_retained_pct: float


# ---------------------------------------------------------------------------
# clean_contacts
# ---------------------------------------------------------------------------


class CleanContactsRequest(BaseModel):
    """
    Mirrors clean_contacts.py's own real CLI parameters
    (--input/--output/--quiet), just typed.
    """

    input_path: str
    output_path: str
    verbose: bool = True


class CleanContactsTool(BaseZeoTool):
    """Rebuild of agency-data-onboarding-kit's scripts/clean_contacts.py."""

    name = "clean_contacts"
    version = "1.0.0"

    def run(
        self, request: CleanContactsRequest, ctx: ToolContext
    ) -> CapabilityResult[CleaningStats]:
        logger = ctx.require_logger()

        try:
            df = pl.read_csv(request.input_path)
        except Exception as e:  # noqa: BLE001 -- mirrors the original's own broad read-error handling, now returned as a typed failure instead of sys.exit
            return CapabilityResult.fail_from_exc(
                msg=f"Could not read input CSV: {request.input_path}",
                code="QC_IO_READ_FAILED",
                exc=e,
            )

        original_count = len(df)
        if logger is not None:
            logger.info(f"[{self.name}] loaded {original_count} rows")

        # Step 1: normalize column names
        df = df.rename({col: normalize_column_name(col) for col in df.columns})

        # Step 2: find/clean the email column (required -- original sys.exit(1)s
        # here; we return a typed failure instead)
        if "email" not in df.columns:
            found = False
            for alt in ("email_address", "e_mail", "contact_email"):
                if alt in df.columns:
                    df = df.rename({alt: "email"})
                    found = True
                    break
            if not found:
                return CapabilityResult.fail(
                    msg="No email column found in input CSV",
                    code="QC_VAL_NO_EMAIL_COLUMN",
                )

        df = df.with_columns(
            [pl.col("email").str.to_lowercase().str.strip_chars().alias("email")]
        )

        # Step 3: extract domain from email
        df = df.with_columns(
            [pl.col("email").str.split("@").list.get(1).alias("email_domain")]
        )

        # Step 4: standardize fields
        if "country" in df.columns:
            df = df.with_columns(
                [
                    pl.col("country")
                    .map_elements(normalize_country, return_dtype=pl.Utf8)
                    .alias("country")
                ]
            )
        if "phone" in df.columns:
            df = df.with_columns(
                [
                    pl.col("phone")
                    .map_elements(clean_phone, return_dtype=pl.Utf8)
                    .alias("phone")
                ]
            )
        if "linkedin" in df.columns:
            df = df.with_columns(
                [
                    pl.col("linkedin")
                    .map_elements(clean_linkedin_url, return_dtype=pl.Utf8)
                    .alias("linkedin")
                ]
            )
        if "full_name" in df.columns:
            df = df.with_columns([pl.col("full_name").str.strip_chars().alias("full_name")])
        if "title" in df.columns:
            df = df.with_columns(
                [
                    pl.col("title")
                    .str.strip_chars()
                    .map_elements(
                        lambda x: None if x == "N/A" else x, return_dtype=pl.Utf8
                    )
                    .alias("title")
                ]
            )

        # Step 5: filter invalid emails
        before_filter = len(df)
        df = df.filter(pl.col("email").map_elements(is_valid_email, return_dtype=pl.Boolean))
        invalid_count = before_filter - len(df)

        # Step 6: completeness score
        completeness_fields = [
            f for f in ("full_name", "email", "title", "phone", "linkedin") if f in df.columns
        ]
        if completeness_fields:
            score_expr = None
            for field in completeness_fields:
                field_score = pl.col(field).is_not_null().cast(pl.Int32)
                score_expr = field_score if score_expr is None else score_expr + field_score
            df = df.with_columns([score_expr.alias("completeness_score")])

        # Step 7: dedupe by email, keep most complete
        before_dedup = len(df)
        df = df.sort("completeness_score", descending=True).unique(
            subset=["email"], keep="first"
        )
        if "completeness_score" in df.columns:
            df = df.drop("completeness_score")
        duplicate_count = before_dedup - len(df)

        # Step 8: metadata + export
        df = df.with_columns([pl.lit("sheet").alias("source")])
        final_count = len(df)

        output_dir = Path(request.output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            df.write_csv(request.output_path)
        except Exception as e:  # noqa: BLE001 -- mirrors the original's own broad write-error handling
            return CapabilityResult.fail_from_exc(
                msg=f"Could not write output CSV: {request.output_path}",
                code="QC_IO_WRITE_FAILED",
                exc=e,
            )

        stats = CleaningStats(
            original_count=original_count,
            invalid_filtered=invalid_count,
            duplicates_removed=duplicate_count,
            final_count=final_count,
            data_retained_pct=round((final_count / original_count) * 100, 1)
            if original_count > 0
            else 0.0,
        )

        if logger is not None:
            logger.info(f"[{self.name}] {stats.final_count} clean contacts written")

        return CapabilityResult.ok(
            data=stats,
            msg=f"Cleaned {stats.final_count} contacts",
            metadata={"tool": f"{self.name} v{self.version}"},
        )


# ---------------------------------------------------------------------------
# clean_accounts
# ---------------------------------------------------------------------------


class CleanAccountsRequest(BaseModel):
    """Mirrors clean_accounts.py's own real CLI parameters, just typed."""

    input_path: str
    output_path: str
    verbose: bool = Field(default=True)


class CleanAccountsTool(BaseZeoTool):
    """Rebuild of agency-data-onboarding-kit's scripts/clean_accounts.py."""

    name = "clean_accounts"
    version = "1.0.0"

    def run(
        self, request: CleanAccountsRequest, ctx: ToolContext
    ) -> CapabilityResult[CleaningStats]:
        logger = ctx.require_logger()

        try:
            df = pl.read_csv(request.input_path)
        except Exception as e:  # noqa: BLE001 -- mirrors the original's own broad read-error handling
            return CapabilityResult.fail_from_exc(
                msg=f"Could not read input CSV: {request.input_path}",
                code="QC_IO_READ_FAILED",
                exc=e,
            )

        original_count = len(df)
        if logger is not None:
            logger.info(f"[{self.name}] loaded {original_count} rows")

        df = df.rename({col: normalize_column_name(col) for col in df.columns})

        # Find/standardize the name column (required)
        name_col = next(
            (c for c in ("name", "company_name", "company", "account_name") if c in df.columns),
            None,
        )
        if name_col is None:
            return CapabilityResult.fail(
                msg="Could not find company name column in input CSV",
                code="QC_VAL_NO_NAME_COLUMN",
            )
        if name_col != "name":
            df = df.rename({name_col: "name"})
        df = df.with_columns([pl.col("name").str.strip_chars().alias("name")])

        # Find/standardize website -> domain
        website_col = next(
            (c for c in ("website", "web_site", "url", "domain") if c in df.columns), None
        )
        if website_col:
            if website_col != "website":
                df = df.rename({website_col: "website"})
            df = df.with_columns(
                [
                    pl.col("website").str.to_lowercase().str.strip_chars().alias("website"),
                    pl.col("website")
                    .map_elements(extract_domain, return_dtype=pl.Utf8)
                    .alias("domain"),
                ]
            )
        else:
            df = df.with_columns([pl.lit(None, dtype=pl.Utf8).alias("domain")])

        if "country" in df.columns:
            df = df.with_columns(
                [
                    pl.col("country")
                    .map_elements(normalize_country, return_dtype=pl.Utf8)
                    .alias("country")
                ]
            )
        if "industry" in df.columns:
            df = df.with_columns(
                [pl.col("industry").str.strip_chars().str.to_titlecase().alias("industry")]
            )
        if "employee_count" in df.columns:
            df = df.with_columns(
                [pl.col("employee_count").cast(pl.Int32, strict=False).alias("employee_count")]
            )
        if "status" in df.columns:
            df = df.with_columns(
                [pl.col("status").str.to_lowercase().str.strip_chars().alias("status")]
            )
        else:
            df = df.with_columns([pl.lit("prospect").alias("status")])

        # Filter: must have a name
        before_filter = len(df)
        df = df.filter(pl.col("name").is_not_null() & (pl.col("name") != ""))
        invalid_count = before_filter - len(df)

        # Completeness score
        completeness_fields = [
            f for f in ("name", "domain", "industry", "employee_count", "country") if f in df.columns
        ]
        if completeness_fields:
            score_expr = None
            for field in completeness_fields:
                field_score = pl.col(field).is_not_null().cast(pl.Int32)
                score_expr = field_score if score_expr is None else score_expr + field_score
            df = df.with_columns([score_expr.alias("completeness_score")])

        # Dedupe: by domain where present, else by lowercased name
        before_dedup = len(df)
        df_with_domain = df.filter(pl.col("domain").is_not_null())
        df_without_domain = df.filter(pl.col("domain").is_null())

        if len(df_with_domain) > 0:
            df_with_domain = df_with_domain.sort("completeness_score", descending=True).unique(
                subset=["domain"], keep="first"
            )
        if len(df_without_domain) > 0:
            df_without_domain = df_without_domain.with_columns(
                [pl.col("name").str.to_lowercase().alias("name_lower")]
            )
            df_without_domain = (
                df_without_domain.sort("completeness_score", descending=True)
                .unique(subset=["name_lower"], keep="first")
                .drop("name_lower")
            )

        if len(df_with_domain) > 0 and len(df_without_domain) > 0:
            df = pl.concat([df_with_domain, df_without_domain])
        elif len(df_with_domain) > 0:
            df = df_with_domain
        else:
            df = df_without_domain

        if "completeness_score" in df.columns:
            df = df.drop("completeness_score")
        duplicate_count = before_dedup - len(df)

        df = df.with_columns([pl.lit("sheet").alias("source")])
        final_count = len(df)

        output_dir = Path(request.output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            df.write_csv(request.output_path)
        except Exception as e:  # noqa: BLE001 -- mirrors the original's own broad write-error handling
            return CapabilityResult.fail_from_exc(
                msg=f"Could not write output CSV: {request.output_path}",
                code="QC_IO_WRITE_FAILED",
                exc=e,
            )

        stats = CleaningStats(
            original_count=original_count,
            invalid_filtered=invalid_count,
            duplicates_removed=duplicate_count,
            final_count=final_count,
            data_retained_pct=round((final_count / original_count) * 100, 1)
            if original_count > 0
            else 0.0,
        )

        if logger is not None:
            logger.info(f"[{self.name}] {stats.final_count} clean accounts written")

        return CapabilityResult.ok(
            data=stats,
            msg=f"Cleaned {stats.final_count} accounts",
            metadata={"tool": f"{self.name} v{self.version}"},
        )
