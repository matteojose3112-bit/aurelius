from datetime import date, datetime
from uuid import uuid4

import pytest

from app.persistence.posting_service import (
    InvalidJournal,
    PostJournalCommand,
    PostingLine,
)


def valid_command():
    return PostJournalCommand(
        owner_id=1,
        actor_id=1,
        effective_date=date(2026, 11, 17),
        description="test journal",
        currency_definition_id=uuid4(),
        postings=(
            PostingLine(uuid4(), "DEBIT", 100),
            PostingLine(uuid4(), "CREDIT", 100),
        ),
    )


def test_posting_line_normalizes_side_and_accepts_integer_minor_units():
    line = PostingLine(uuid4(), "debit", 100)
    assert line.side == "DEBIT"
    assert line.amount_minor == 100


@pytest.mark.parametrize("amount", [True, 1.0, "100", 0, -1, 10**38])
def test_posting_line_rejects_non_integer_or_out_of_range_minor_units(amount):
    with pytest.raises((TypeError, ValueError)):
        PostingLine(uuid4(), "DEBIT", amount)


def test_posting_command_rejects_unbalanced_lines():
    currency_id = uuid4()
    with pytest.raises(InvalidJournal, match="debits must equal credits"):
        PostJournalCommand(
            owner_id=1,
            actor_id=1,
            effective_date=date(2026, 11, 17),
            description="unbalanced",
            currency_definition_id=currency_id,
            postings=(
                PostingLine(uuid4(), "DEBIT", 100),
                PostingLine(uuid4(), "CREDIT", 99),
            ),
        )


def test_posting_command_rejects_duplicate_account_lines():
    currency_id = uuid4()
    account_id = uuid4()
    with pytest.raises(InvalidJournal, match="only once"):
        PostJournalCommand(
            owner_id=1,
            actor_id=1,
            effective_date=date(2026, 11, 17),
            description="duplicate account",
            currency_definition_id=currency_id,
            postings=(
                PostingLine(account_id, "DEBIT", 100),
                PostingLine(account_id, "CREDIT", 100),
            ),
        )


def test_posting_command_rejects_datetime_as_effective_date():
    command = valid_command()
    with pytest.raises(TypeError, match="calendar date"):
        PostJournalCommand(
            owner_id=command.owner_id,
            actor_id=command.actor_id,
            effective_date=datetime(2026, 11, 17, 12, 0),
            description=command.description,
            currency_definition_id=command.currency_definition_id,
            postings=command.postings,
        )


def test_posting_command_rejects_boolean_owner_id():
    command = valid_command()
    with pytest.raises(ValueError, match="owner_id"):
        PostJournalCommand(
            owner_id=True,
            actor_id=command.actor_id,
            effective_date=command.effective_date,
            description=command.description,
            currency_definition_id=command.currency_definition_id,
            postings=command.postings,
        )
