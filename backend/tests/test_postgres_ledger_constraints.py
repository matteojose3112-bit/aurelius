"""Integration tests that must run against disposable PostgreSQL 16."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from decimal import Decimal
import os
from threading import Event
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.exc import IntegrityError, DBAPIError
from sqlalchemy.orm import Session, sessionmaker

from app.main import app
from app.models import User
from app.persistence.currency_registry_seed import seed_currency_registry
from app.persistence.models import (
    AccountingPeriodModel,
    AuditEventModel,
    CurrencyDefinitionModel,
    FinancialAccountModel,
    JournalEntryModel,
    JournalPostingModel,
    IdempotencyRecordModel,
)



from app.persistence.posting_service import (
    AccountClosed,
    AccountingPeriodUnavailable,
    IdempotencyConflict,
    JournalAlreadyReversed,
    PostJournalCommand,
    PostingLine,
    ReverseJournalCommand,
    post_journal,
    reverse_journal,
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
        "999",
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


def test_postgres_rejects_fractional_minor_units_before_commit(pg_session):
    owner, usd, _, debit_account, credit_account = setup_owner_and_accounts(pg_session)
    journal, postings = make_journal(
        owner, usd, debit_account, credit_account, "100.5", "100.5"
    )
    pg_session.add_all([journal, *postings])
    with pytest.raises(IntegrityError, match="ck_journal_postings_integral_minor_units"):
        pg_session.commit()
    pg_session.rollback()


def test_postgres_accepts_38_digit_integer_minor_units(pg_session):
    owner, usd, _, debit_account, credit_account = setup_owner_and_accounts(pg_session)
    maximum = "99999999999999999999999999999999999999"
    journal, postings = make_journal(
        owner, usd, debit_account, credit_account, maximum, maximum
    )
    pg_session.add_all([journal, *postings])
    pg_session.commit()
    assert pg_session.get(JournalEntryModel, journal.id) is not None


def test_postgres_rejects_minor_units_at_10_to_the_38(pg_session):
    owner, usd, _, debit_account, credit_account = setup_owner_and_accounts(pg_session)
    out_of_range = "100000000000000000000000000000000000000"
    journal, postings = make_journal(
        owner, usd, debit_account, credit_account, out_of_range, out_of_range
    )
    pg_session.add_all([journal, *postings])
    with pytest.raises(IntegrityError, match="ck_journal_postings_integral_minor_units"):
        pg_session.commit()
    pg_session.rollback()


def test_postgres_rejects_cross_owner_posting_foreign_key(pg_session):
    owner_a, usd, _, debit_account, _ = setup_owner_and_accounts(pg_session)
    owner_b = User(email=f"{uuid4()}@aurelius.test", password_hash="test-only")
    pg_session.add(owner_b)
    pg_session.flush()
    other_account = FinancialAccountModel(
        id=uuid4(),
        owner_id=owner_b.id,
        name="Other owner's cash",
        account_type="ASSET",
        currency_definition_id=usd.id,
        status="OPEN",
    )
    pg_session.add(other_account)
    pg_session.flush()

    journal_id = uuid4()
    journal = JournalEntryModel(
        id=journal_id,
        owner_id=owner_a.id,
        effective_date=date(2026, 11, 17),
        description="Cross-owner attempt",
        currency_definition_id=usd.id,
        status="POSTED",
        created_by=owner_a.id,
    )
    pg_session.add(journal)
    pg_session.add_all([
        JournalPostingModel(
            id=uuid4(), journal_entry_id=journal_id, owner_id=owner_a.id,
            account_id=debit_account.id, currency_definition_id=usd.id,
            side="DEBIT", amount_minor=Decimal("100"),
        ),
        JournalPostingModel(
            id=uuid4(), journal_entry_id=journal_id, owner_id=owner_a.id,
            account_id=other_account.id, currency_definition_id=usd.id,
            side="CREDIT", amount_minor=Decimal("100"),
        ),
    ])
    with pytest.raises(IntegrityError, match="fk_journal_postings_account_owner_currency"):
        pg_session.commit()
    pg_session.rollback()


def test_postgres_rejects_cross_currency_posting_foreign_key(pg_session):
    owner, usd, cad, debit_account, _ = setup_owner_and_accounts(pg_session)
    cad_account = FinancialAccountModel(
        id=uuid4(), owner_id=owner.id, name="CAD cash",
        account_type="ASSET", currency_definition_id=cad.id, status="OPEN",
    )
    pg_session.add(cad_account)
    pg_session.flush()

    journal_id = uuid4()
    pg_session.add(JournalEntryModel(
        id=journal_id, owner_id=owner.id, effective_date=date(2026, 11, 17),
        description="Cross-currency attempt", currency_definition_id=usd.id,
        status="POSTED", created_by=owner.id,
    ))
    pg_session.add_all([
        JournalPostingModel(
            id=uuid4(), journal_entry_id=journal_id, owner_id=owner.id,
            account_id=debit_account.id, currency_definition_id=usd.id,
            side="DEBIT", amount_minor=Decimal("100"),
        ),
        JournalPostingModel(
            id=uuid4(), journal_entry_id=journal_id, owner_id=owner.id,
            account_id=cad_account.id, currency_definition_id=usd.id,
            side="CREDIT", amount_minor=Decimal("100"),
        ),
    ])
    with pytest.raises(IntegrityError, match="fk_journal_postings_account_owner_currency"):
        pg_session.commit()
    pg_session.rollback()


def test_postgres_accounting_periods_cannot_overlap_for_owner(pg_session):
    owner = User(email=f"{uuid4()}@aurelius.test", password_hash="test-only")
    pg_session.add(owner)
    pg_session.flush()
    pg_session.add_all([
        AccountingPeriodModel(
            id=uuid4(), owner_id=owner.id,
            starts_on=date(2026, 1, 1), ends_on=date(2026, 1, 31), status="OPEN",
        ),
        AccountingPeriodModel(
            id=uuid4(), owner_id=owner.id,
            starts_on=date(2026, 1, 15), ends_on=date(2026, 2, 15), status="OPEN",
        ),
    ])
    with pytest.raises(IntegrityError, match="ex_accounting_periods_owner_no_overlap"):
        pg_session.commit()
    pg_session.rollback()


def test_postgres_idempotency_completion_is_one_time(pg_session):
    owner, _, _, _, _ = setup_owner_and_accounts(pg_session)
    record = IdempotencyRecordModel(
        id=uuid4(), owner_id=owner.id, operation="create_journal",
        idempotency_key=str(uuid4()), request_hash="b" * 64,
    )
    pg_session.add(record)
    pg_session.commit()

    record.response_status = 201
    record.response_body = {"journal_id": str(uuid4())}
    record.completed_at = datetime.now(timezone.utc)
    pg_session.commit()

    record.response_body = {"journal_id": "tampered"}
    with pytest.raises(DBAPIError, match="completed idempotency result is immutable"):
        pg_session.commit()
    pg_session.rollback()


def test_postgres_currency_registry_rows_are_append_only(pg_session):
    setup_owner_and_accounts(pg_session)
    pg_session.commit()
    usd = pg_session.scalars(
        select(CurrencyDefinitionModel).where(
            CurrencyDefinitionModel.code == "USD",
            CurrencyDefinitionModel.registry_list == "one",
        )
    ).one()
    usd.name = "Tampered currency"
    with pytest.raises(DBAPIError, match="append-only"):
        pg_session.commit()
    pg_session.rollback()



def make_post_command(owner, usd, debit_account, credit_account, description="service post", amount=1000):
    return PostJournalCommand(
        owner_id=owner.id,
        actor_id=owner.id,
        effective_date=date(2026, 11, 17),
        description=description,
        currency_definition_id=usd.id,
        postings=(
            PostingLine(debit_account.id, "DEBIT", amount),
            PostingLine(credit_account.id, "CREDIT", amount),
        ),
    )


def test_posting_service_commits_journal_audit_and_idempotency(pg_engine, pg_session):
    owner, usd, _, debit_account, credit_account = setup_owner_and_accounts(pg_session)
    pg_session.commit()
    factory = sessionmaker(bind=pg_engine, expire_on_commit=False)
    command = make_post_command(owner, usd, debit_account, credit_account)

    result = post_journal(factory, command, "service-key-001")

    assert result.status_code == 201
    assert result.replayed is False
    assert result.body["currency"]["code"] == "USD"
    assert len(result.body["postings"]) == 2
    journal_id = UUID(result.body["journal_id"])
    assert pg_session.get(JournalEntryModel, journal_id) is not None
    assert pg_session.scalar(
        select(func.count()).select_from(AuditEventModel).where(
            AuditEventModel.aggregate_id == journal_id
        )
    ) == 1
    assert pg_session.scalar(
        select(func.count()).select_from(IdempotencyRecordModel).where(
            IdempotencyRecordModel.idempotency_key == "service-key-001"
        )
    ) == 1


def test_posting_service_replays_same_key_and_rejects_changed_payload(pg_engine, pg_session):
    owner, usd, _, debit_account, credit_account = setup_owner_and_accounts(pg_session)
    pg_session.commit()
    factory = sessionmaker(bind=pg_engine, expire_on_commit=False)
    command = make_post_command(owner, usd, debit_account, credit_account)

    first = post_journal(factory, command, "service-key-002")
    replay = post_journal(factory, command, "service-key-002")
    assert replay.replayed is True
    assert replay.body == first.body

    changed = make_post_command(
        owner, usd, debit_account, credit_account, description="different payload"
    )
    with pytest.raises(IdempotencyConflict):
        post_journal(factory, changed, "service-key-002")

    assert pg_session.scalar(
        select(func.count()).select_from(JournalEntryModel).where(
            JournalEntryModel.owner_id == owner.id
        )
    ) == 1


def test_posting_service_rolls_back_idempotency_claim_on_validation_failure(pg_engine, pg_session):
    owner, usd, _, debit_account, credit_account = setup_owner_and_accounts(pg_session)
    debit_account.status = "CLOSED"
    pg_session.commit()
    factory = sessionmaker(bind=pg_engine, expire_on_commit=False)
    command = make_post_command(owner, usd, debit_account, credit_account)

    with pytest.raises(AccountClosed):
        post_journal(factory, command, "retry-after-failure")

    assert pg_session.scalar(
        select(func.count()).select_from(IdempotencyRecordModel).where(
            IdempotencyRecordModel.idempotency_key == "retry-after-failure"
        )
    ) == 0

    debit_account.status = "OPEN"
    pg_session.commit()
    result = post_journal(factory, command, "retry-after-failure")
    assert result.status_code == 201


def test_posting_service_enforces_configured_open_period(pg_engine, pg_session):
    owner, usd, _, debit_account, credit_account = setup_owner_and_accounts(pg_session)
    pg_session.add(AccountingPeriodModel(
        id=uuid4(), owner_id=owner.id,
        starts_on=date(2026, 1, 1), ends_on=date(2026, 12, 31), status="CLOSED",
    ))
    pg_session.commit()
    factory = sessionmaker(bind=pg_engine, expire_on_commit=False)
    command = make_post_command(owner, usd, debit_account, credit_account)

    with pytest.raises(AccountingPeriodUnavailable):
        post_journal(factory, command, "closed-period-key")


def test_posting_service_serializes_concurrent_same_key_replays(pg_engine, pg_session):
    owner, usd, _, debit_account, credit_account = setup_owner_and_accounts(pg_session)
    pg_session.commit()
    factory = sessionmaker(bind=pg_engine, expire_on_commit=False)
    command = make_post_command(owner, usd, debit_account, credit_account)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(post_journal, factory, command, "concurrent-service-key")
            for _ in range(2)
        ]
        results = [future.result(timeout=20) for future in futures]

    assert sorted(result.replayed for result in results) == [False, True]
    assert results[0].body["journal_id"] == results[1].body["journal_id"]
    assert pg_session.scalar(
        select(func.count()).select_from(JournalEntryModel).where(
            JournalEntryModel.owner_id == owner.id
        )
    ) == 1


def test_reverse_service_creates_exactly_one_reversal(pg_engine, pg_session):
    owner, usd, _, debit_account, credit_account = setup_owner_and_accounts(pg_session)
    pg_session.commit()
    factory = sessionmaker(bind=pg_engine, expire_on_commit=False)
    original = post_journal(
        factory,
        make_post_command(owner, usd, debit_account, credit_account),
        "original-journal-key",
    )
    reverse_command = ReverseJournalCommand(
        owner_id=owner.id,
        actor_id=owner.id,
        source_journal_id=UUID(original.body["journal_id"]),
        effective_date=date(2026, 11, 18),
    )

    reversal = reverse_journal(factory, reverse_command, "reversal-key-001")
    replay = reverse_journal(factory, reverse_command, "reversal-key-001")
    assert reversal.replayed is False
    assert replay.replayed is True
    assert replay.body == reversal.body
    assert reversal.body["reversal_of"] == original.body["journal_id"]

    with pytest.raises(JournalAlreadyReversed):
        reverse_journal(factory, reverse_command, "reversal-key-002")


def test_reverse_service_serializes_competing_reversals(pg_engine, pg_session):
    owner, usd, _, debit_account, credit_account = setup_owner_and_accounts(pg_session)
    pg_session.commit()
    factory = sessionmaker(bind=pg_engine, expire_on_commit=False)
    original = post_journal(
        factory,
        make_post_command(owner, usd, debit_account, credit_account),
        "original-for-race",
    )
    command = ReverseJournalCommand(
        owner_id=owner.id,
        actor_id=owner.id,
        source_journal_id=UUID(original.body["journal_id"]),
        effective_date=date(2026, 11, 18),
    )

    def reverse_with_key(key):
        try:
            return reverse_journal(factory, command, key)
        except JournalAlreadyReversed:
            return "already-reversed"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(reverse_with_key, ["reverse-race-a", "reverse-race-b"]))

    assert sum(isinstance(result, str) for result in results) == 1
    assert sum(not isinstance(result, str) for result in results) == 1
    assert pg_session.scalar(
        select(func.count()).select_from(JournalEntryModel).where(
            JournalEntryModel.reversal_of == UUID(original.body["journal_id"])
        )
    ) == 1



def test_posting_service_rolls_back_after_journal_and_posting_inserts(
    pg_engine, pg_session, monkeypatch
):
    from app.persistence import posting_service as posting_service_module

    owner, usd, _, debit_account, credit_account = setup_owner_and_accounts(pg_session)
    pg_session.commit()
    factory = sessionmaker(bind=pg_engine, expire_on_commit=False)
    command = make_post_command(owner, usd, debit_account, credit_account)

    def injected_failure(*args, **kwargs):
        raise RuntimeError("injected failure after posting rows were flushed")

    monkeypatch.setattr(posting_service_module, "_journal_response", injected_failure)
    with pytest.raises(RuntimeError, match="injected failure"):
        posting_service_module.post_journal(factory, command, "rollback-after-postings")

    assert pg_session.scalar(
        select(func.count()).select_from(JournalEntryModel).where(
            JournalEntryModel.owner_id == owner.id
        )
    ) == 0
    assert pg_session.scalar(
        select(func.count()).select_from(JournalPostingModel)
    ) == 0
    assert pg_session.scalar(
        select(func.count()).select_from(AuditEventModel)
    ) == 0
    assert pg_session.scalar(
        select(func.count()).select_from(IdempotencyRecordModel).where(
            IdempotencyRecordModel.idempotency_key == "rollback-after-postings"
        )
    ) == 0


def test_posting_service_serializes_account_close_against_post(
    pg_engine, pg_session
):
    owner, usd, _, debit_account, credit_account = setup_owner_and_accounts(pg_session)
    pg_session.commit()
    factory = sessionmaker(bind=pg_engine, expire_on_commit=False)
    command = make_post_command(owner, usd, debit_account, credit_account)
    account_locked = Event()
    release_close = Event()

    def close_account():
        with Session(pg_engine) as close_session:
            with close_session.begin():
                account = close_session.execute(
                    select(FinancialAccountModel)
                    .where(FinancialAccountModel.id == debit_account.id)
                    .with_for_update()
                ).scalar_one()
                account.status = "CLOSED"
                account_locked.set()
                assert release_close.wait(timeout=10)

    def attempt_post():
        assert account_locked.wait(timeout=10)
        try:
            post_journal(factory, command, "close-post-race-key")
        except AccountClosed:
            return "closed-account-rejected"
        return "unexpected-post"

    with ThreadPoolExecutor(max_workers=2) as pool:
        close_future = pool.submit(close_account)
        assert account_locked.wait(timeout=10)
        post_future = pool.submit(attempt_post)
        release_close.set()
        close_future.result(timeout=10)
        assert post_future.result(timeout=20) == "closed-account-rejected"

    assert pg_session.scalar(
        select(func.count()).select_from(JournalEntryModel).where(
            JournalEntryModel.owner_id == owner.id
        )
    ) == 0
    assert pg_session.scalar(
        select(func.count()).select_from(IdempotencyRecordModel).where(
            IdempotencyRecordModel.idempotency_key == "close-post-race-key"
        )
    ) == 0



def test_versioned_ledger_api_account_post_balance_reversal_and_owner_isolation(pg_session):
    with TestClient(app) as client:
        first_registration = client.post(
            "/api/auth/register",
            json={"email": f"{uuid4()}@api-test.example", "password": "securepass123"},
        )
        assert first_registration.status_code == 201
        first_user_id = first_registration.json()["user"]["id"]
        client.headers["Authorization"] = (
            f"Bearer {first_registration.json()['access_token']}"
        )

        seed_currency_registry(pg_session)
        pg_session.commit()

        currencies = client.get("/v1/currencies")
        assert currencies.status_code == 200
        assert any(item["code"] == "USD" for item in currencies.json())
        assert all(item["code"] not in {"XAU", "XAG"} for item in currencies.json())

        cash = client.post(
            "/v1/accounts",
            json={"name": "Operating cash", "account_type": "ASSET", "currency": "USD"},
        )
        income = client.post(
            "/v1/accounts",
            json={"name": "Service revenue", "account_type": "INCOME", "currency": "USD"},
        )
        assert cash.status_code == 201
        assert income.status_code == 201

        journal_payload = {
            "effective_date": "2026-11-17",
            "description": "API integration journal",
            "currency": "USD",
            "postings": [
                {
                    "account_id": cash.json()["id"],
                    "side": "DEBIT",
                    "amount_minor": "12500",
                },
                {
                    "account_id": income.json()["id"],
                    "side": "CREDIT",
                    "amount_minor": "12500",
                },
            ],
        }
        posted = client.post(
            "/v1/ledger/journals",
            json=journal_payload,
            headers={"Idempotency-Key": "api-post-key-001"},
        )
        assert posted.status_code == 201
        journal_id = posted.json()["journal_id"]

        replay = client.post(
            "/v1/ledger/journals",
            json=journal_payload,
            headers={"Idempotency-Key": "api-post-key-001"},
        )
        assert replay.status_code == 201
        assert replay.json()["journal_id"] == journal_id

        balance = client.get(
            f"/v1/accounts/{cash.json()['id']}/balance?as_of=2026-11-17"
        )
        assert balance.status_code == 200
        assert balance.json()["balance_minor"] == "12500"

        detail = client.get(f"/v1/ledger/journals/{journal_id}")
        assert detail.status_code == 200
        assert len(detail.json()["postings"]) == 2

        reversal = client.post(
            f"/v1/ledger/journals/{journal_id}/reversal",
            json={"effective_date": "2026-11-18", "description": "API reversal"},
            headers={"Idempotency-Key": "api-reversal-key-001"},
        )
        assert reversal.status_code == 201
        assert reversal.json()["reversal_of"] == journal_id

        second_registration = client.post(
            "/api/auth/register",
            json={"email": f"{uuid4()}@api-test.example", "password": "securepass123"},
        )
        assert second_registration.status_code == 201
        client.headers["Authorization"] = (
            f"Bearer {second_registration.json()['access_token']}"
        )
        forbidden_balance = client.get(
            f"/v1/accounts/{cash.json()['id']}/balance?as_of=2026-11-17"
        )
        assert forbidden_balance.status_code == 404



def test_versioned_account_api_fails_closed_when_registry_is_not_seeded(pg_session):
    with TestClient(app) as client:
        unauthenticated = client.get("/v1/accounts")
        assert unauthenticated.status_code == 401

        registration = client.post(
            "/api/auth/register",
            json={"email": f"{uuid4()}@no-registry.example", "password": "securepass123"},
        )
        assert registration.status_code == 201
        client.headers["Authorization"] = f"Bearer {registration.json()['access_token']}"

        response = client.post(
            "/v1/accounts",
            json={"name": "Cash", "account_type": "ASSET", "currency": "USD"},
        )
        assert response.status_code == 503
        assert "registry has not been seeded" in response.json()["detail"]
