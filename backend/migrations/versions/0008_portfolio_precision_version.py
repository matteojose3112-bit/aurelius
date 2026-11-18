"""Version portfolio lot monetary precision without rewriting history."""

from alembic import op
import sqlalchemy as sa


revision = "0008_portfolio_precision_version"
down_revision = "0006_settlement_account_mapping"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "trade_executions",
        sa.Column(
            "accounting_precision_version",
            sa.SmallInteger(),
            nullable=False,
            server_default="1",
        ),
    )
    op.create_check_constraint(
        "ck_trade_executions_precision_version",
        "trade_executions",
        "accounting_precision_version IN (1, 2)",
    )


def downgrade():
    op.drop_constraint(
        "ck_trade_executions_precision_version",
        "trade_executions",
        type_="check",
    )
    op.drop_column("trade_executions", "accounting_precision_version")
