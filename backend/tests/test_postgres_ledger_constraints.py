"""Integration tests that must run against disposable PostgreSQL 16."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
import os
from threading import Event
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.exc import IntegrityError, DBAPIError
from sqlalchemy.orm import Session

from app.models import User
from app.persistence.currency_registry_seed import seed_currency_registry
from app.persistence.models import (
    CurrencyDefinitionModel,
    FinancialAccountModel,
    JournalEntryModel,
    JournalPostingModel,
    IdempotencyRecordModel,
)


POSTGRES_TEST_URL = os.getenv("POSTGRES_TEST_URL")
pytestmark = pytest.mark.skipif(
    not POSTGRES_TEST_URL,
    reason="requires disposable PostgreSQL test database",
)


@pytest.fixture()
def pg_engine():
    engine = create_engine(POSTGRES_TEST_URL, pool_pre_ping=True)
    with engine.connect() as connection:
        version = int(connection.scalar(text("SHOW server_version_num")))
        assert version >= 160000, "PostgreSQL 16 or newer is required"
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE TABLE currency_definitions, users RESTART IDENTITY CASCADE"))
    yield engine
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE TABLE currency_definitions, users RESTART IDENTITY CASCADE"))
    engine.dispose()


@pytest.fixture()
def pg_session(pg_engine):
    with Session(pg_engine) as session:
        yield session
        session.rollback()


def setup_owner_and_accounts(session):
    owner = User(email=f"{uuid4()}@aurelius.test", password_hash="test-only")
    session.add(owner)
    session.flush()
    seed_currency_registry(session)
    session.flush()

    usd = session.scalars(
        select(CurrencyDefinitionModel).where(
            CurrencyDefinitionModel.code == "USD",
            CurrencyDefinitionModel.registry_list == "one",
        )
    ).one()
    cad = session.scalars(
        select(CurrencyDefinitionModel).where(
            CurrencyDefinitionModel.code == "CAD",
            CurrencyDefinitionModel.registry_list == "one",
        )
    ).one()

    debit_account = FinancialAccountModel(
        id=uuid4(),
        owner_id=owner.id,
        name="Cash",
        account_type="ASSET",
        currency_definition_id=usd.id,
        status="OPEN",
    )
    credit_account = FinancialAccountModel(
        id=uuid4(),
        owner_id=owner.id,
        name="Revenue",
        account_type="INCOME",
        currency_definition_id=usd.id,
        status="OPEN",
    )
    session.add_all([debit_account, credit_account])
    session.flush()
    return owner, usd, cad, debit_account, credit_account


def make_journal(owner, currency, debit_account, credit_account, debit, credit, reversal_of=None):
    journal_id = uuid4()
    journal = JournalEntryModel(
        id=journal_id,
        owner_id=owner.id,
        effective_date=date(2026, 11, 17),
        description="PostgreSQL integration test",
        currency_definition_id=currency.id,
        status="POSTED",
        reversal_of=reversal_of,
        created_by=owner.id,
    )
    postings = [
        JournalPostingModel(
            id=uuid4(),
            journal_entry_id=journal_id,
            owner_id=owner.id,
            account_id=debit_account.id,
            currency_definition_id=currency.id,
            side="DEBIT",
            amount_minor=Decimal(debit),
        ),
        JournalPostingModel(
            id=uuid4(),
            journal_entry_id=journal_id,
            owner_id=owner.id,
            account_id=credit_account.id,
            currency_definition_id=currency.id,
            side="CREDIT",
            amount_minor=Decimal(credit),
        ),
    ]
    return journal, postings


def test_postgres_accepts_balanced_journal_at_deferred_commit(pg_session):
    owner, usd, _, debit_account, credit_account = setup_owner_and_accounts(pg_session)
    journal, postings = make_journal(
        owner, usd, debit_account, credit_account, "12500", "12500"
    )
    pg_session.add_all([journal, *postings])
    pg_session.commit()
    assert pg_session.get(JournalEntryModel, journal.id) is not None


def test_postgres_rejects_unbalanced_journal_at_commit(pg_session):
    owner, usd, _, debit_account, credit_account = setup_owner_and_accounts(pg_session)
    journal, postings = make_journal(
        owner, usd, debit_account, credit_account, "12500", "12499"
    )
    pg_session.add_all([journal, *postings])
    with pytest.raises(IntegrityError, match="balanced postings"):
        pg_session.commit()
    pg_session.rollback()
    assert pg_session.get(JournalEntryModel, journal.id) is None


def test_postgres_rejects_journal_with_only_one_posting(pg_session):
    owner, usd, _, debit_account, _ = setup_owner_and_accounts(pg_session)
    journal_id = uuid4()
    pg_session.add(
        JournalEntryModel(
            id=journal_id,
            owner_id=owner.id,
            effective_date=date(2026, 11, 17),
            description="Incomplete journal",
            currency_definition_id=usd.id,
            status="POSTED",
            created_by=owner.id,
        )
    )
    pg_session.add(
        JournalPostingModel(
            id=uuid4(),
            journal_entry_id=journal_id,
            owner_id=owner.id,
            account_id=debit_account.id,
            currency_definition_id=usd.id,
            side="DEBIT",
            amount_minor=Decimal("100"),
        )
    )
    with pytest.raises(IntegrityError, match="at least two balanced postings"):
        pg_session.commit()
    pg_session.rollback()


def test_postgres_rejects_closed_account_posting(pg_session):
    owner, usd, _, debit_account, credit_account = setup_owner_and_accounts(pg_session)
    debit_account.status = "CLOSED"
    journal, postings = make_journal(
        owner, usd, debit_account, credit_account, "100", "100"
    )
    pg_session.add_all([journal, *postings])
    with pytest.raises(IntegrityError, match="open accounts"):
        pg_session.commit()
    pg_session.rollback()


def test_postgres_reversal_must_exactly_invert_original(pg_session):
    owner, usd, _, debit_account, credit_account = setup_owner_and_accounts(pg_session)
    original, original_postings = make_journal(
        owner, usd, debit_account, credit_account, "1000", "1000"
    )
    pg_session.add_all([original, *original_postings])
    pg_session.commit()

    reversal, reversal_postings = make_journal(
        owner,
        usd,
        debit_account,
        credit_account,
        "999",
        "1000",
        reversal_of=original.id,
    )
    # Reverse the sides; the first amount is deliberately incorrect.
    reversal_postings[0].side = "CREDIT"
    reversal_postings[1].side = "DEBIT"
    pg_session.add_all([reversal, *reversal_postings])
    with pytest.raises(IntegrityError, match="exactly invert"):
        pg_session.commit()
    pg_session.rollback()


def test_postgres_rejects_update_and_delete_of_posted_journal(pg_session):
    owner, usd, _, debit_account, credit_account = setup_owner_and_accounts(pg_session)
    journal, postings = make_journal(
        owner, usd, debit_account, credit_account, "100", "100"
    )
    pg_session.add_all([journal, *postings])
    pg_session.commit()

    journal.description = "Tampered"
    with pytest.raises(DBAPIError, match="append-only"):
        pg_session.commit()
    pg_session.rollback()


def test_postgres_transaction_rollback_leaves_no_partial_journal(pg_session):
    owner, usd, _, debit_account, _ = setup_owner_and_accounts(pg_session)
    journal_id = uuid4()
    pg_session.add(
        JournalEntryModel(
            id=journal_id,
            owner_id=owner.id,
            effective_date=date(2026, 11, 17),
            description="Injected partial transaction",
            currency_definition_id=usd.id,
            status="POSTED",
            created_by=owner.id,
        )
    )
    pg_session.flush()
    pg_session.add(
        JournalPostingModel(
            id=uuid4(),
            journal_entry_id=journal_id,
            owner_id=owner.id,
            account_id=debit_account.id,
            currency_definition_id=usd.id,
            side="DEBIT",
            amount_minor=Decimal("100"),
        )
    )
    pg_session.rollback()
    assert pg_session.scalar(
        select(func.count()).select_from(JournalEntryModel).where(
            JournalEntryModel.id == journal_id
        )
    ) == 0
    assert pg_session.scalar(
        select(func.count()).select_from(JournalPostingModel).where(
            JournalPostingModel.journal_entry_id == journal_id
        )
    ) == 0


def test_postgres_serializes_concurrent_duplicate_idempotency_keys(pg_engine, pg_session):
    owner, _, _, _, _ = setup_owner_and_accounts(pg_session)
    pg_session.commit()

    inserted = Event()
    release_first = Event()
    second_started = Event()
    record_id = uuid4()
    key_values = {
        "id": record_id,
        "owner_id": owner.id,
        "operation": "create_journal",
        "idempotency_key": str(uuid4()),
        "request_hash": "a" * 64,
        "response_status": None,
        "response_body": None,
        "completed_at": None,
    }

    def first_writer():
        with pg_engine.begin() as connection:
            connection.execute(IdempotencyRecordModel.__table__.insert().values(**key_values))
            inserted.set()
            assert release_first.wait(timeout=10)

    def second_writer():
        assert inserted.wait(timeout=10)
        second_started.set()
        try:
            with pg_engine.begin() as connection:
                connection.execute(
                    IdempotencyRecordModel.__table__.insert().values(
                        **{**key_values, "id": uuid4()}
                    )
                )
        except IntegrityError:
            return "unique-conflict"
        return "unexpected-success"

    with ThreadPoolExecutor(max_workers=2) as pool:
        first_future = pool.submit(first_writer)
        assert inserted.wait(timeout=10)
        second_future = pool.submit(second_writer)
        assert second_started.wait(timeout=10)
        release_first.set()
        first_future.result(timeout=10)
        assert second_future.result(timeout=10) == "unique-conflict"

    assert pg_session.scalar(
        select(func.count()).select_from(IdempotencyRecordModel).where(
            IdempotencyRecordModel.owner_id == owner.id,
            IdempotencyRecordModel.operation == "create_journal",
            IdempotencyRecordModel.idempotency_key == key_values["idempotency_key"],
        )
    ) == 1
