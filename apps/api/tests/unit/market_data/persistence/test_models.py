"""
Unit tests for MarketDataBarModel persistence model.
===================================================
Verifies bidirectional domain mapping, numeric precision preservation,
and UTC timestamp normalization.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from app.modules.market_data.domain.models import (
    AdjustmentPolicy,
    DataInterval,
    Instrument,
    OHLCVRecord,
)
from app.modules.market_data.infrastructure.persistence.models import MarketDataBarModel


class TestMarketDataBarModel:
    def test_from_domain_mapping(self, sample_instrument: Instrument) -> None:
        """Verify converting canonical OHLCVRecord into MarketDataBarModel."""
        record = OHLCVRecord(
            symbol="AAPL",
            timestamp=datetime(2024, 1, 2, 14, 30, tzinfo=UTC),
            open=185.25,
            high=187.50,
            low=184.10,
            close=186.90,
            volume=5000000.0,
            interval=DataInterval.ONE_DAY,
            adjustment_policy=AdjustmentPolicy.SPLIT_ADJUSTED,
            source_provider_id="yahoo_finance",
        )

        model = MarketDataBarModel.from_domain(record, sample_instrument)

        assert model.symbol == "AAPL"
        assert model.asset_class == "equity_us"
        assert model.exchange == "NASDAQ"
        assert model.interval == "1d"
        assert model.timestamp == datetime(2024, 1, 2, 14, 30, tzinfo=UTC)
        assert model.open == Decimal("185.25")
        assert model.high == Decimal("187.5")
        assert model.low == Decimal("184.1")
        assert model.close == Decimal("186.9")
        assert model.volume == Decimal("5000000.0")
        assert model.adjustment_policy == "split_adjusted"
        assert model.source_provider_id == "yahoo_finance"

    def test_to_domain_mapping(self) -> None:
        """Verify converting MarketDataBarModel back into canonical OHLCVRecord."""
        model = MarketDataBarModel(
            symbol="AAPL",
            asset_class="equity_us",
            exchange="NASDAQ",
            interval="1d",
            timestamp=datetime(2024, 1, 2, 14, 30, tzinfo=UTC),
            open=Decimal("185.250000"),
            high=Decimal("187.500000"),
            low=Decimal("184.100000"),
            close=Decimal("186.900000"),
            volume=Decimal("5000000.000000"),
            adjustment_policy="raw",
            source_provider_id="test_provider",
            created_at=datetime(2024, 1, 2, 15, 0, tzinfo=UTC),
            updated_at=datetime(2024, 1, 2, 15, 0, tzinfo=UTC),
        )

        domain = model.to_domain()

        assert domain.symbol == "AAPL"
        assert domain.interval == DataInterval.ONE_DAY
        assert domain.adjustment_policy == AdjustmentPolicy.RAW
        assert domain.open == 185.25
        assert domain.high == 187.5
        assert domain.low == 184.1
        assert domain.close == 186.9
        assert domain.volume == 5000000.0
        assert domain.source_provider_id == "test_provider"
        assert domain.timestamp.tzinfo is not None

    def test_numeric_precision_roundtrip(self) -> None:
        """Verify high decimal precision is preserved."""
        model = MarketDataBarModel(
            symbol="BTC-USD",
            asset_class="crypto",
            exchange="COINBASE",
            interval="1h",
            timestamp=datetime(2024, 1, 2, 14, 0, tzinfo=UTC),
            open=Decimal("42123.123456"),
            high=Decimal("42500.654321"),
            low=Decimal("42000.000001"),
            close=Decimal("42300.999999"),
            volume=Decimal("1234.567891"),
            adjustment_policy="raw",
            source_provider_id="crypto_provider",
            created_at=datetime(2024, 1, 2, 15, 0, tzinfo=UTC),
            updated_at=datetime(2024, 1, 2, 15, 0, tzinfo=UTC),
        )

        assert model.open == Decimal("42123.123456")
        assert model.high == Decimal("42500.654321")
        assert model.low == Decimal("42000.000001")
        assert model.close == Decimal("42300.999999")
        assert model.volume == Decimal("1234.567891")
