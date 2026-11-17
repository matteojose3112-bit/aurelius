"""Immutable market observations and model forecasts, kept as separate domains."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
import re
from uuid import UUID


@dataclass(frozen=True, slots=True)
class MarketObservation:
    observation_id: UUID
    instrument_id: UUID
    observation_type: str
    value: Decimal
    source_id: str
    observed_at: datetime
    retrieved_at: datetime
    unit_code: str | None = None
    quote_currency_code: str | None = None
    market_session: str | None = None
    methodology: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.observation_id, UUID) or not isinstance(self.instrument_id, UUID):
            raise TypeError("market observation IDs must be UUID")
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", self.observation_type):
            raise ValueError("observation_type must be a lowercase identifier")
        if not isinstance(self.value, Decimal) or not self.value.is_finite():
            raise ValueError("market observation value must be a finite Decimal")
        if not self.source_id.strip():
            raise ValueError("market observation source_id is required")
        for name in ("observed_at", "retrieved_at"):
            value = getattr(self, name)
            if not isinstance(value, datetime) or value.tzinfo is None:
                raise ValueError(f"{name} must be timezone-aware")
        if self.retrieved_at < self.observed_at:
            raise ValueError("retrieved_at cannot precede observed_at")
        if self.quote_currency_code is not None and not re.fullmatch(
            r"[A-Z]{3}", self.quote_currency_code
        ):
            raise ValueError("quote currency must be ISO alpha-3")


@dataclass(frozen=True, slots=True)
class ForecastRecord:
    forecast_id: UUID
    target_id: str
    model_id: str
    model_version: str
    probability: Decimal
    generated_at: datetime
    horizon_end: datetime
    evidence_ids: tuple[str, ...] = ()
    resolved_outcome: str | None = None
    resolved_at: datetime | None = None
    scoring_method: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.forecast_id, UUID):
            raise TypeError("forecast_id must be UUID")
        if not self.target_id.strip() or not self.model_id.strip() or not self.model_version.strip():
            raise ValueError("forecast target, model ID, and version are required")
        if not isinstance(self.probability, Decimal) or not self.probability.is_finite():
            raise ValueError("forecast probability must be a finite Decimal")
        if not Decimal("0") <= self.probability <= Decimal("1"):
            raise ValueError("forecast probability must be between zero and one")
        for name in ("generated_at", "horizon_end"):
            value = getattr(self, name)
            if not isinstance(value, datetime) or value.tzinfo is None:
                raise ValueError(f"{name} must be timezone-aware")
        if self.horizon_end < self.generated_at:
            raise ValueError("forecast horizon cannot precede generation time")
        evidence = tuple(self.evidence_ids)
        if any(not item.strip() for item in evidence):
            raise ValueError("forecast evidence identifiers must be non-empty")
        object.__setattr__(self, "evidence_ids", evidence)
        if (self.resolved_outcome is None) != (self.resolved_at is None):
            raise ValueError("resolved forecasts require both an outcome and resolved_at")
        if self.resolved_outcome is not None and not self.resolved_outcome.strip():
            raise ValueError("resolved forecast outcome must be non-empty")
        if self.resolved_at is not None and self.resolved_at.tzinfo is None:
            raise ValueError("resolved_at must be timezone-aware")
