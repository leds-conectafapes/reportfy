"""Shared period utilities for biweekly (half-month) calculations."""
from __future__ import annotations

import pandas as pd


def half_month_period(dt: pd.Timestamp) -> pd.Timestamp:
    """
    Map a timestamp to the start of its half-month period.

    The organisation always uses two fixed periods per calendar month:
      - **First half** (days 1–15)  → returns the 1st of the month.
      - **Second half** (days 16–31) → returns the 16th of the month.

    This guarantees consistent, human-readable period labels
    (e.g. "2026-04-01" and "2026-04-16") instead of the rolling
    14-day windows produced by ``pd.Period("2W")``.

    Args:
        dt: Any pandas Timestamp.  NaT values should be filtered before
            calling this function.

    Returns:
        Timestamp set to the 1st or 16th of the same month/year.

    Examples::

        half_month_period(pd.Timestamp("2026-04-03"))  # → 2026-04-01
        half_month_period(pd.Timestamp("2026-04-20"))  # → 2026-04-16
    """
    day = 1 if dt.day <= 15 else 16
    return pd.Timestamp(year=dt.year, month=dt.month, day=day)


def apply_half_month(series: pd.Series) -> pd.Series:
    """
    Vectorised wrapper — apply ``half_month_period`` to a datetime Series.

    Args:
        series: A pandas Series of Timestamps (NaT values are propagated as NaT).

    Returns:
        A new Series of Timestamps representing period starts.
    """
    s = pd.Series(series) if not isinstance(series, pd.Series) else series
    return s.apply(
        lambda v: pd.NaT if pd.isna(v) else half_month_period(pd.Timestamp(v))
    )
