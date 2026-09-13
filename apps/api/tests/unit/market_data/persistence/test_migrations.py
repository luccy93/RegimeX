"""
Unit tests for Alembic database migrations.
===========================================
Validates that the initial market data migration:
1. Upgrades cleanly to head on an empty database.
2. Creates expected tables, columns, constraints, and indexes.
3. Downgrades cleanly back to base.
4. Re-upgrades cleanly to head (reversibility and idempotency).
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import sqlalchemy as sa
from alembic import command
from alembic.config import Config


class TestMarketDataMigrations:
    def test_migration_lifecycle(self) -> None:
        """
        Verify complete migration lifecycle:
        upgrade(head) -> verify schema -> downgrade(base) -> verify clean -> upgrade(head).
        """
        api_root = Path(__file__).resolve().parents[4]
        alembic_ini_path = api_root / "alembic.ini"
        alembic_scripts_path = api_root / "alembic"

        assert alembic_ini_path.exists(), f"alembic.ini not found at {alembic_ini_path}"
        assert alembic_scripts_path.exists(), (
            f"alembic directory not found at {alembic_scripts_path}"
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "test_migration.db"
            db_url = f"sqlite:///{db_path.as_posix()}"

            # Configure Alembic to target the temporary SQLite database
            alembic_cfg = Config(str(alembic_ini_path))
            alembic_cfg.set_main_option("sqlalchemy.url", db_url)
            alembic_cfg.set_main_option("script_location", str(alembic_scripts_path))

            # --- Phase 1: Upgrade to head ---
            command.upgrade(alembic_cfg, "head")

            sync_engine = sa.create_engine(db_url)
            try:
                inspector = sa.inspect(sync_engine)
                tables = inspector.get_table_names()
                assert "market_data_bars" in tables, f"Expected market_data_bars in {tables}"

                # Verify column names
                columns = {col["name"]: col for col in inspector.get_columns("market_data_bars")}
                expected_columns = {
                    "id",
                    "symbol",
                    "asset_class",
                    "exchange",
                    "interval",
                    "timestamp",
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume",
                    "adjustment_policy",
                    "source_provider_id",
                    "created_at",
                    "updated_at",
                }
                assert expected_columns.issubset(set(columns.keys())), (
                    f"Missing columns: {expected_columns - set(columns.keys())}"
                )

                # Verify non-null constraints
                assert not columns["symbol"]["nullable"]
                assert not columns["timestamp"]["nullable"]
                assert not columns["close"]["nullable"]
                assert not columns["volume"]["nullable"]

                # Verify indexes exist
                indexes = inspector.get_indexes("market_data_bars")
                index_names = {idx["name"] for idx in indexes}
                assert any("symbol" in name for name in index_names if name)

                # --- Phase 2: Downgrade to base ---
                command.downgrade(alembic_cfg, "base")

                inspector = sa.inspect(sync_engine)
                tables_after_downgrade = inspector.get_table_names()
                assert "market_data_bars" not in tables_after_downgrade

                # --- Phase 3: Re-upgrade to head ---
                command.upgrade(alembic_cfg, "head")

                inspector = sa.inspect(sync_engine)
                tables_after_reupgrade = inspector.get_table_names()
                assert "market_data_bars" in tables_after_reupgrade

            finally:
                sync_engine.dispose()
