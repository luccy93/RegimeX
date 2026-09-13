"""Initial market data storage schema

Revision ID: 0001_initial_market_data
Revises: None
Create Date: 2026-09-14 00:00:00.000000+00:00

"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_initial_market_data"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Create market_data_bars table
    op.create_table(
        "market_data_bars",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("symbol", sa.String(length=50), nullable=False),
        sa.Column("asset_class", sa.String(length=20), nullable=False),
        sa.Column("exchange", sa.String(length=20), nullable=False),
        sa.Column("interval", sa.String(length=10), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("high", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("low", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("close", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("volume", sa.Numeric(precision=24, scale=6), nullable=False),
        sa.Column("adjustment_policy", sa.String(length=20), nullable=False, server_default="raw"),
        sa.Column("source_provider_id", sa.String(length=100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_market_data_bars"),
        sa.UniqueConstraint(
            "symbol",
            "interval",
            "timestamp",
            name="uq_market_data_symbol_interval_ts",
        ),
    )

    # 2. Indexes for queries
    op.create_index(
        "ix_market_data_bars_symbol",
        "market_data_bars",
        ["symbol"],
        unique=False,
    )
    op.create_index(
        "ix_market_data_bars_timestamp",
        "market_data_bars",
        ["timestamp"],
        unique=False,
    )
    op.create_index(
        "ix_market_data_symbol_interval_ts",
        "market_data_bars",
        ["symbol", "interval", "timestamp"],
        unique=False,
    )
    op.create_index(
        "ix_market_data_symbol_ts",
        "market_data_bars",
        ["symbol", "timestamp"],
        unique=False,
    )

    # 3. Optional TimescaleDB hypertable conversion (PostgreSQL only)
    bind = op.get_bind()
    if bind is not None and bind.dialect.name == "postgresql":
        op.execute(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM pg_extension WHERE extname = 'timescaledb'
                ) THEN
                    PERFORM create_hypertable('market_data_bars', 'timestamp', if_not_exists => TRUE);
                END IF;
            END $$;
            """
        )


def downgrade() -> None:
    op.drop_index("ix_market_data_symbol_ts", table_name="market_data_bars")
    op.drop_index("ix_market_data_symbol_interval_ts", table_name="market_data_bars")
    op.drop_index("ix_market_data_bars_timestamp", table_name="market_data_bars")
    op.drop_index("ix_market_data_bars_symbol", table_name="market_data_bars")
    op.drop_table("market_data_bars")
