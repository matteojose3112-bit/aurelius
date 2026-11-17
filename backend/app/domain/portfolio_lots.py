"""Deterministic long-only portfolio lot accounting.

This domain is intentionally separate from cash-ledger posting, market prices,
tax rules, and broker execution. It records trade fills and derives open lots.
Jurisdiction-specific tax treatment belongs in a later policy layer.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal, InvalidOperation, localcontext
from enum import Enum
from typing import Iterable
from uuid import UUID, NAMESPACE_URL, uuid5


class CostBasisMethod(str, Enum):
    FIFO = "fifo"
    LIFO = "lifo"
    SPECIFIC = "specific"


class TradeSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class PortfolioAccountingError(ValueError):
    """A trade cannot be applied without violating portfolio invariants."""


@dataclass(frozen=True, slots=True)
class TradeExecution:
    execution_id: UUID
    portfolio_id: UUID
    account_id: UUID
    instrument_id: UUID
    side: TradeSide
    quantity: Decimal
    unit_price: Decimal
    quote_currency_code: str
    fee: Decimal
    executed_at: datetime
    source: str

    def __post_init__(self) -> None:
        for field in ("execution_id", "portfolio_id", "account_id", "instrument_id"):
            if not isinstance(getattr(self, field), UUID):
                raise TypeError(f"{field} must be UUID")
        if not isinstance(self.side, TradeSide):
            raise TypeError("side must be a TradeSide")
        for field in ("quantity", "unit_price", "fee"):
            value = getattr(self, field)
            if isinstance(value, (float, bool)) or not isinstance(value, Decimal):
                raise TypeError(f"{field} must be Decimal; binary floats are prohibited")
            if not value.is_finite():
                raise ValueError(f"{field} must be finite")
        if self.quantity <= 0:
            raise ValueError("trade quantity must be positive")
        if self.unit_price < 0:
            raise ValueError("unit price cannot be negative")
        if self.fee < 0:
            raise ValueError("trade fee cannot be negative")
        if not self.quote_currency_code or len(self.quote_currency_code) != 3 or not self.quote_currency_code.isalpha() or self.quote_currency_code.upper() != self.quote_currency_code:
            raise ValueError("quote currency must be an uppercase three-letter code")
        if not isinstance(self.executed_at, datetime) or self.executed_at.tzinfo is None:
            raise ValueError("executed_at must be timezone-aware")
        if not self.source.strip():
            raise ValueError("trade source is required")


@dataclass(frozen=True, slots=True)
class TaxLot:
    lot_id: UUID
    portfolio_id: UUID
    account_id: UUID
    instrument_id: UUID
    quote_currency_code: str
    opened_by_execution_id: UUID
    opened_at: datetime
    original_quantity: Decimal
    remaining_quantity: Decimal
    original_cost: Decimal
    remaining_cost: Decimal

    def __post_init__(self) -> None:
        if self.original_quantity <= 0 or self.remaining_quantity < 0:
            raise ValueError("lot quantities are outside valid bounds")
        if self.remaining_quantity > self.original_quantity:
            raise ValueError("remaining lot quantity exceeds original quantity")
        if self.original_cost < 0 or self.remaining_cost < 0:
            raise ValueError("lot cost cannot be negative")
        if self.remaining_cost > self.original_cost:
            raise ValueError("remaining lot cost exceeds original cost")


@dataclass(frozen=True, slots=True)
class DisposalAllocation:
    lot_id: UUID
    quantity: Decimal
    cost_basis: Decimal
    gross_proceeds: Decimal
    allocated_sale_fee: Decimal
    net_proceeds: Decimal
    realized_gain_loss: Decimal


@dataclass(frozen=True, slots=True)
class TradeApplication:
    execution_id: UUID
    opened_lot_id: UUID | None
    allocations: tuple[DisposalAllocation, ...]
    realized_gain_loss: Decimal
    replayed: bool = False


@dataclass(frozen=True, slots=True)
class PositionSnapshot:
    portfolio_id: UUID
    account_id: UUID
    instrument_id: UUID
    quote_currency_code: str
    quantity: Decimal
    remaining_cost_basis: Decimal

    @property
    def average_cost(self) -> Decimal | None:
        if self.quantity == 0:
            return None
        return self.remaining_cost_basis / self.quantity


def _fingerprint(execution: TradeExecution) -> tuple[object, ...]:
    return (
        execution.portfolio_id, execution.account_id, execution.instrument_id,
        execution.side, execution.quantity, execution.unit_price,
        execution.quote_currency_code, execution.fee, execution.executed_at,
        execution.source,
    )


class PortfolioLotBook:
    """In-memory deterministic lot aggregate; persistence is a separate adapter."""

    def __init__(self) -> None:
        self._lots: dict[UUID, TaxLot] = {}
        self._executions: dict[UUID, tuple[tuple[object, ...], TradeApplication]] = {}

    @property
    def lots(self) -> tuple[TaxLot, ...]:
        return tuple(sorted(self._lots.values(), key=lambda item: (item.opened_at, str(item.lot_id))))

    def apply(
        self,
        execution: TradeExecution,
        *,
        cost_basis_method: CostBasisMethod = CostBasisMethod.FIFO,
        specific_lot_id: UUID | None = None,
    ) -> TradeApplication:
        fingerprint = _fingerprint(execution)
        prior = self._executions.get(execution.execution_id)
        if prior is not None:
            if prior[0] != fingerprint:
                raise PortfolioAccountingError("execution ID was reused with a different payload")
            return replace(prior[1], replayed=True)

        if not isinstance(cost_basis_method, CostBasisMethod):
            raise TypeError("cost_basis_method must be CostBasisMethod")
        if cost_basis_method is CostBasisMethod.SPECIFIC and specific_lot_id is None:
            raise PortfolioAccountingError("specific-lot disposal requires a lot ID")
        if cost_basis_method is not CostBasisMethod.SPECIFIC and specific_lot_id is not None:
            raise PortfolioAccountingError("specific_lot_id is only valid with SPECIFIC method")

        if execution.side is TradeSide.BUY:
            result = self._buy(execution)
        else:
            result = self._sell(execution, cost_basis_method, specific_lot_id)

        self._executions[execution.execution_id] = (fingerprint, result)
        return result

    def _buy(self, execution: TradeExecution) -> TradeApplication:
        total_cost = execution.quantity * execution.unit_price + execution.fee
        lot_id = uuid5(NAMESPACE_URL, f"aurelius:portfolio-lot:{execution.execution_id}")
        lot = TaxLot(
            lot_id=lot_id,
            portfolio_id=execution.portfolio_id,
            account_id=execution.account_id,
            instrument_id=execution.instrument_id,
            quote_currency_code=execution.quote_currency_code,
            opened_by_execution_id=execution.execution_id,
            opened_at=execution.executed_at,
            original_quantity=execution.quantity,
            remaining_quantity=execution.quantity,
            original_cost=total_cost,
            remaining_cost=total_cost,
        )
        self._lots[lot_id] = lot
        return TradeApplication(execution.execution_id, lot_id, (), Decimal("0"))

    def _sell(
        self,
        execution: TradeExecution,
        method: CostBasisMethod,
        specific_lot_id: UUID | None,
    ) -> TradeApplication:
        eligible = [
            lot for lot in self._lots.values()
            if lot.portfolio_id == execution.portfolio_id
            and lot.account_id == execution.account_id
            and lot.instrument_id == execution.instrument_id
            and lot.quote_currency_code == execution.quote_currency_code
            and lot.remaining_quantity > 0
        ]
        eligible.sort(key=lambda item: (item.opened_at, str(item.lot_id)))
        if method is CostBasisMethod.LIFO:
            eligible.reverse()
        elif method is CostBasisMethod.SPECIFIC:
            eligible = [lot for lot in eligible if lot.lot_id == specific_lot_id]
            if not eligible:
                raise PortfolioAccountingError("specific lot is not open in this position")

        available = sum((lot.remaining_quantity for lot in eligible), Decimal("0"))
        if available < execution.quantity:
            raise PortfolioAccountingError("sale quantity exceeds available long position")

        # Plan all allocations before mutating lots, so validation failures are atomic.
        remaining_to_sell = execution.quantity
        planned: list[tuple[TaxLot, Decimal, Decimal]] = []
        with localcontext() as context:
            context.prec = 50
            for lot in eligible:
                if remaining_to_sell == 0:
                    break
                take = min(lot.remaining_quantity, remaining_to_sell)
                if take == lot.remaining_quantity:
                    basis = lot.remaining_cost
                else:
                    basis = lot.remaining_cost * take / lot.remaining_quantity
                planned.append((lot, take, basis))
                remaining_to_sell -= take

            gross_total = execution.quantity * execution.unit_price
            allocated_fee_total = Decimal("0")
            allocations: list[DisposalAllocation] = []
            for index, (lot, quantity, basis) in enumerate(planned):
                if index == len(planned) - 1:
                    sale_fee = execution.fee - allocated_fee_total
                else:
                    sale_fee = execution.fee * quantity / execution.quantity
                    allocated_fee_total += sale_fee
                gross = quantity * execution.unit_price
                net = gross - sale_fee
                allocations.append(
                    DisposalAllocation(
                        lot_id=lot.lot_id,
                        quantity=quantity,
                        cost_basis=basis,
                        gross_proceeds=gross,
                        allocated_sale_fee=sale_fee,
                        net_proceeds=net,
                        realized_gain_loss=net - basis,
                    )
                )

            for lot, quantity, basis in planned:
                self._lots[lot.lot_id] = replace(
                    lot,
                    remaining_quantity=lot.remaining_quantity - quantity,
                    remaining_cost=lot.remaining_cost - basis,
                )

        realized = sum((item.realized_gain_loss for item in allocations), Decimal("0"))
        return TradeApplication(execution.execution_id, None, tuple(allocations), realized)

    def position(
        self, portfolio_id: UUID, account_id: UUID, instrument_id: UUID,
        quote_currency_code: str,
    ) -> PositionSnapshot:
        matching = [
            lot for lot in self._lots.values()
            if lot.portfolio_id == portfolio_id
            and lot.account_id == account_id
            and lot.instrument_id == instrument_id
            and lot.quote_currency_code == quote_currency_code
            and lot.remaining_quantity > 0
        ]
        return PositionSnapshot(
            portfolio_id=portfolio_id,
            account_id=account_id,
            instrument_id=instrument_id,
            quote_currency_code=quote_currency_code,
            quantity=sum((lot.remaining_quantity for lot in matching), Decimal("0")),
            remaining_cost_basis=sum((lot.remaining_cost for lot in matching), Decimal("0")),
        )
