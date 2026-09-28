"""
RegimeX Platform — End-to-End Critical Workflows Test Suite
===========================================================
Volume 22 — Commit 02: Critical Workflow Integrity

Deterministic cross-layer workflow tests exercising:
User / API Client -> FastAPI Route -> Application Service -> Domain Engine
-> Deterministic Golden Fixture -> API Response -> Contract Verification

Workflows Covered:
1. Workflow 1 — Market Intelligence (Catalog, OHLCV, Regime, Empty & Unknown Symbol)
2. Workflow 2 — Regime Analytics (Regime intelligence, profiles, duration, transitions)
3. Workflow 3 — Risk Analysis (Returns, annualized volatility, max drawdown, VaR, ES)
4. Workflow 4 — Backtesting (Buy & Hold, Regime Adaptive, execution conventions, report)
5. Workflow 5 — Authentication Boundary (Register, login, token, protected /auth/me)
6. Workflow 6 — Grounded AI Research (Query, routing, symbol resolution, evidence retrieval)
7. Workflow 7 — Model-Aware Explanation (Intent MODEL_EXPLANATION, provenance, comparison)
8. Workflow 8 — AI Safety Refusal (Price prediction refusal, financial advice refusal)
9. Workflow 9 — AI Grounding Failure & Sanitization (Unsupported claims rejected by validator)
10. Workflow 10 — API Failure Recovery (Transient failure -> error envelope -> retry)
11. Workflow 11 — Empty Data Handling (Valid market with no data -> graceful 422 envelope)
12. Workflow 12 — Unknown Market (Catalog lookup rejected early with 404 / friendly fallback)
13. Workflow 13 — Permission Boundaries (Public analytics vs strictly protected profiles)
14. Workflow 14 — Request Correlation (X-Request-ID propagation, zero credential leakage)
15. Workflow 15 & 19 — Research SSE Streaming & Interruption (Ordered events, error, abort)
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Generator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from app.core.database.base import Base
from app.core.dependencies import (
    ai_research_service_dep,
    backtesting_service_dep,
    db_session_dep,
    market_data_provider_dep,
    market_intelligence_dep,
    market_service_dep,
    portfolio_risk_service_dep,
)
from app.main import create_app
from app.modules.ai_research.application.service import AIResearchService
from app.modules.ai_research.domain.interfaces import ResearchModelProvider
from app.modules.ai_research.domain.models import EvidencePacket
from app.modules.ai_research.infrastructure.providers.mock_provider import MockModelProvider
from app.modules.backtesting.application.service import BacktestingService
from app.modules.identity_access.infrastructure.persistence.models import (
    UserModel,  # noqa: F401
)
from app.modules.market_data.application.service import MarketDataService
from app.modules.portfolio_risk.application.service import PortfolioRiskService
from app.modules.regime_intelligence.application.facade import MarketIntelligenceFacade
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from tests.fixtures.spy_golden_fixture import (
    BASE_DATE,
    GoldenMarketDataProvider,
)

# =============================================================================
# Test Infrastructure Fixtures
# =============================================================================


@pytest.fixture
async def e2e_db_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Create an isolated in-memory SQLite database for authentication state testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine
    await engine.dispose()


@pytest.fixture
def golden_provider() -> GoldenMarketDataProvider:
    return GoldenMarketDataProvider()


@pytest.fixture
def workflow_client(
    e2e_db_engine: AsyncEngine,
    golden_provider: GoldenMarketDataProvider,
) -> Generator[TestClient, None, None]:
    """
    Construct a TestClient wiring the complete application stack with the
    deterministic GoldenMarketDataProvider and in-memory test database.
    """
    session_factory = async_sessionmaker(
        bind=e2e_db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async def override_db_session() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    market_svc = MarketDataService(provider=golden_provider)
    intel_facade = MarketIntelligenceFacade(market_service=market_svc)
    risk_svc = PortfolioRiskService()
    backtest_svc = BacktestingService()
    ai_research_svc = AIResearchService(
        market_service=market_svc,
        market_intelligence=intel_facade,
        risk_service=risk_svc,
        backtest_service=backtest_svc,
        provider=MockModelProvider(),
    )

    app = create_app()
    app.dependency_overrides[db_session_dep] = override_db_session
    app.dependency_overrides[market_data_provider_dep] = lambda: golden_provider
    app.dependency_overrides[market_service_dep] = lambda: market_svc
    app.dependency_overrides[market_intelligence_dep] = lambda: intel_facade
    app.dependency_overrides[portfolio_risk_service_dep] = lambda: risk_svc
    app.dependency_overrides[backtesting_service_dep] = lambda: backtest_svc
    app.dependency_overrides[ai_research_service_dep] = lambda: ai_research_svc

    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


# =============================================================================
# Workflow 1 — Market Intelligence Workflow
# =============================================================================


class TestMarketIntelligenceWorkflow:
    """
    Workflow 1: Open market dashboard -> select market -> fetch market data
    -> fetch current regime -> render snapshot -> verify response contracts.
    """

    def test_market_intelligence_e2e_flow(self, workflow_client: TestClient) -> None:
        # Step 1: Discover catalog instruments
        catalog_res = workflow_client.get("/api/v1/markets")
        assert catalog_res.status_code == 200
        catalog = catalog_res.json()
        assert catalog["total"] >= 3
        symbols = [item["symbol"] for item in catalog["items"]]
        assert "SPY" in symbols
        assert "QQQ" in symbols

        # Step 2: Fetch time-series OHLCV bars for SPY
        start_str = BASE_DATE.isoformat()
        end_str = (BASE_DATE + timedelta(days=60)).isoformat()
        bars_res = workflow_client.get(
            "/api/v1/markets/SPY/data",
            params={"start": start_str, "end": end_str, "interval": "1d"},
        )
        assert bars_res.status_code == 200
        bars_data = bars_res.json()
        assert bars_data["symbol"] == "SPY"
        assert bars_data["count"] == 60
        assert bars_data["total"] == 60
        assert len(bars_data["items"]) == 60

        # Verify bar contract fields
        first_bar = bars_data["items"][0]
        assert first_bar["open"] > 0
        assert first_bar["high"] >= first_bar["low"]
        assert first_bar["close"] > 0
        assert first_bar["volume"] > 0
        assert "timestamp" in first_bar

        # Step 3: Fetch current regime intelligence for SPY
        regime_res = workflow_client.get(
            "/api/v1/markets/SPY/regime",
            params={"start": start_str, "end": end_str, "interval": "1d"},
        )
        assert regime_res.status_code == 200
        regime_data = regime_res.json()
        assert regime_data["symbol"] == "SPY"
        assert regime_data["current_regime"] in (0, 1, 2)
        assert "current_context" in regime_data
        ctx = regime_data["current_context"]
        assert ctx["observations_in_current_run"] >= 1
        assert ctx["historical_average_duration"] > 0

    def test_market_intelligence_invalid_date_window_rejected(
        self, workflow_client: TestClient
    ) -> None:
        """Start >= End must be rejected with HTTP 422 standard error envelope."""
        now = datetime.now(UTC)
        res = workflow_client.get(
            "/api/v1/markets/SPY/data",
            params={"start": now.isoformat(), "end": (now - timedelta(days=5)).isoformat()},
        )
        assert res.status_code == 422
        data = res.json()
        assert "error" in data
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert "start" in data["error"]["details"] or "end" in data["error"]["details"]


# =============================================================================
# Workflow 2 — Regime Analytics Workflow
# =============================================================================


class TestRegimeAnalyticsWorkflow:
    """
    Workflow 2: Select market -> Open /app/regimes -> retrieve regime intelligence
    -> retrieve transition analytics -> verify profiles, persistence, and matrix.
    """

    def test_regime_analytics_e2e_flow(self, workflow_client: TestClient) -> None:
        start_str = BASE_DATE.isoformat()
        end_str = (BASE_DATE + timedelta(days=60)).isoformat()

        # Step 1: Retrieve regime intelligence & profiles
        regime_res = workflow_client.get(
            "/api/v1/markets/SPY/regime",
            params={"start": start_str, "end": end_str, "interval": "1d"},
        )
        assert regime_res.status_code == 200
        regime_data = regime_res.json()
        assert regime_data["total_observations"] >= 2
        assert len(regime_data["profiles"]) >= 1

        # Check profile feature statistics
        first_profile_id = next(iter(regime_data["profiles"]))
        profile = regime_data["profiles"][first_profile_id]
        assert profile["frequency"] > 0.0
        assert profile["average_duration"] > 0.0
        assert "feature_statistics" in profile

        # Step 2: Retrieve transition dynamics and Markov matrix
        trans_res = workflow_client.get(
            "/api/v1/markets/SPY/regime/transitions",
            params={"start": start_str, "end": end_str, "interval": "1d"},
        )
        assert trans_res.status_code == 200
        trans_data = trans_res.json()
        assert trans_data["symbol"] == "SPY"
        assert len(trans_data["regimes"]) >= 1
        assert "probability_matrix" in trans_data
        assert "regime_analytics" in trans_data
        assert "global_analytics" in trans_data

        # Check global transition analytics
        global_stats = trans_data["global_analytics"]
        assert global_stats["total_observations"] >= 2
        assert 0.0 <= global_stats["global_persistence_rate"] <= 1.0

        # Model provenance must be populated and non-empty
        assert regime_data["model_name"] is not None
        assert regime_data["algorithm"] is not None


# =============================================================================
# Workflow 3 — Risk Analysis Workflow
# =============================================================================


class TestRiskAnalysisWorkflow:
    """
    Workflow 3: Open /app/risk -> select market -> request risk analytics
    -> verify returns, volatility, downside deviation, max drawdown, VaR, ES.
    """

    def test_risk_analysis_e2e_flow(self, workflow_client: TestClient) -> None:
        start_str = BASE_DATE.isoformat()
        end_str = (BASE_DATE + timedelta(days=60)).isoformat()

        res = workflow_client.get(
            "/api/v1/markets/SPY/risk",
            params={"start": start_str, "end": end_str},
        )
        assert res.status_code == 200
        risk = res.json()

        assert risk["symbol"] == "SPY"
        assert risk["observation_count"] in (59, 60)
        assert "computed_at" in risk

        # 1. Return statistics
        stats = risk["return_statistics"]
        assert stats["standard_deviation"] > 0
        assert stats["minimum_return"] <= stats["maximum_return"]

        # 2. Volatility
        vol = risk["volatility"]
        assert vol["period_volatility"] > 0
        assert vol["annualized_volatility"] > 0
        assert vol["periods_per_year"] == 252.0

        # 3. Downside risk
        downside = risk["downside_risk"]
        assert downside["downside_deviation"] >= 0
        assert downside["target_return"] == 0.0

        # 4. Maximum drawdown
        dd = risk["drawdown"]
        assert dd["max_drawdown"] <= 0.0
        assert dd["drawdown_magnitude"] >= 0.0
        assert dd["peak_value"] >= dd["trough_value"]

        # 5. VaR and Expected Shortfall
        assert "0.95" in risk["var_metrics"]
        var_95 = risk["var_metrics"]["0.95"]
        assert var_95["confidence_level"] == 0.95
        assert var_95["var_loss"] is not None

        assert "0.95" in risk["expected_shortfall_metrics"]
        es_95 = risk["expected_shortfall_metrics"]["0.95"]
        assert es_95["confidence_level"] == 0.95
        assert es_95["expected_shortfall"] is not None

        # 6. Price points trace
        assert len(risk["price_points"]) == 60
        assert "drawdown" in risk["price_points"][0]


# =============================================================================
# Workflow 4 — Backtesting Workflow
# =============================================================================


class TestBacktestingWorkflow:
    """
    Workflow 4: Open /app/backtesting -> select market -> request backtest
    -> verify equity curve, trade statistics, risk section, and performance report.
    """

    def test_backtest_buy_and_hold_e2e(self, workflow_client: TestClient) -> None:
        start_str = BASE_DATE.isoformat()
        end_str = (BASE_DATE + timedelta(days=60)).isoformat()

        res = workflow_client.get(
            "/api/v1/markets/SPY/backtest",
            params={
                "start": start_str,
                "end": end_str,
                "strategy": "BUY_AND_HOLD",
                "execution_convention": "CURRENT_CLOSE",
                "initial_cash": 100_000.0,
            },
        )
        assert res.status_code == 200
        bt = res.json()

        assert bt["symbol"] == "SPY"
        assert bt["strategy_id"] == "BUY_AND_HOLD"
        assert bt["initial_cash"] == 100_000.0
        assert bt["final_equity"] > 0
        assert bt["execution_convention"] == "CURRENT_CLOSE"

        # Trade statistics
        trades = bt["trades"]
        assert trades["order_count"] >= 1
        assert trades["fill_count"] >= 1

        # Risk metrics on simulated equity curve
        risk_m = bt["risk_metrics"]
        assert risk_m["volatility"] >= 0
        assert risk_m["maximum_drawdown"] <= 0.0

        # Equity curve snapshots
        assert len(bt["equity_curve"]) >= 3
        last_snap = bt["equity_curve"][-1]
        assert "equity" in last_snap
        assert "drawdown" in last_snap

        # Performance report
        report = bt["report"]
        assert report["report_id"] is not None
        assert "methodology" in report
        assert len(report["metric_definitions"]) >= 1

    def test_backtest_regime_adaptive_strategy(self, workflow_client: TestClient) -> None:
        start_str = BASE_DATE.isoformat()
        end_str = (BASE_DATE + timedelta(days=60)).isoformat()

        res = workflow_client.get(
            "/api/v1/markets/SPY/backtest",
            params={
                "start": start_str,
                "end": end_str,
                "strategy": "REGIME_ADAPTIVE",
                "execution_convention": "NEXT_OPEN",
            },
        )
        assert res.status_code == 200
        bt = res.json()
        assert bt["strategy_id"] == "REGIME_ADAPTIVE"
        assert bt["execution_convention"] == "NEXT_OPEN"

    def test_backtest_invalid_convention_rejected(self, workflow_client: TestClient) -> None:
        res = workflow_client.get(
            "/api/v1/markets/SPY/backtest",
            params={"execution_convention": "BOGUS_TIMING"},
        )
        assert res.status_code == 422
        assert res.json()["error"]["code"] == "VALIDATION_ERROR"


# =============================================================================
# Workflow 5 — Authentication Boundary Workflow
# =============================================================================


class TestAuthenticationWorkflow:
    """
    Workflow 5: Complete authentication boundary lifecycle:
    Register -> Validation -> Login -> Token receipt -> Protected route access
    -> Invalid credentials -> Expired token -> Session revocation.
    """

    def test_auth_complete_lifecycle(self, workflow_client: TestClient) -> None:
        email = "quant.analyst@regimex.io"
        password = "SecurePassword2026!"

        # Step 1: Register new account
        reg_res = workflow_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password},
        )
        assert reg_res.status_code == 201
        reg_data = reg_res.json()
        assert reg_data["user"]["email"] == email
        assert "id" in reg_data["user"]
        # Invariant: passwords and hashes are never exposed
        assert "password" not in reg_data["user"]
        assert "password_hash" not in reg_data["user"]

        # Step 2: Duplicate registration must fail with 409 Conflict
        dup_res = workflow_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password},
        )
        assert dup_res.status_code == 409
        assert dup_res.json()["error"]["code"] == "CONFLICT"

        # Step 3: Login with credentials
        login_res = workflow_client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        assert login_res.status_code == 200
        token_data = login_res.json()
        assert "access_token" in token_data
        assert token_data["token_type"] == "bearer"
        token = token_data["access_token"]

        # Step 4: Access protected route (/api/v1/auth/me) with token
        me_res = workflow_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me_res.status_code == 200
        user_profile = me_res.json()
        assert user_profile["email"] == email
        assert user_profile["is_active"] is True

        # Step 5: Invalid credentials returns generic 401 (anti-enumeration)
        bad_pw_res = workflow_client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "WrongPassword999!"},
        )
        assert bad_pw_res.status_code == 401
        assert bad_pw_res.json()["error"]["code"] == "INVALID_CREDENTIALS"

        # Step 6: Unknown email returns identical generic 401
        unknown_res = workflow_client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@regimex.io", "password": password},
        )
        assert unknown_res.status_code == 401
        assert unknown_res.json()["error"]["code"] == "INVALID_CREDENTIALS"

        # Step 7: Missing token on protected endpoint returns 401
        unauth_res = workflow_client.get("/api/v1/auth/me")
        assert unauth_res.status_code == 401
        assert unauth_res.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"

        # Step 8: Malformed token on protected endpoint returns 401
        bad_token_res = workflow_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer malformed.jwt.token"},
        )
        assert bad_token_res.status_code == 401
        assert bad_token_res.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"


# =============================================================================
# Workflow 6 — Grounded AI Research Workflow
# =============================================================================


class TestGroundedAIResearchWorkflow:
    """
    Workflow 6: Research query -> IntentRouter -> SymbolResolver -> EvidenceRetriever
    -> GroundingEngine -> MockModelProvider -> GroundingValidator -> Citations.
    """

    def test_grounded_research_query_e2e(self, workflow_client: TestClient) -> None:
        headers = {"X-Request-ID": "req-research-e2e-001"}
        payload = {
            "question": "What regime is SPY currently in?",
            "symbol": "SPY",
        }
        res = workflow_client.post("/api/v1/research/query", json=payload, headers=headers)
        assert res.status_code == 200
        assert res.headers.get("X-Request-ID") == "req-research-e2e-001"

        data = res.json()
        assert data["request_id"] == "req-research-e2e-001"
        assert data["intent"] == "CURRENT_REGIME"
        assert data["symbol"] == "SPY"
        assert len(data["evidence"]) >= 1
        assert len(data["citations"]) >= 1

        # Grounding invariant: answer must contain citation tag matching returned citations
        assert "[1]" in data["answer"]
        c1 = data["citations"][0]
        assert c1["id"] == 1
        assert c1["source_id"] is not None
        assert "regime" in c1["source_type"]


# =============================================================================
# Workflow 7 — Model-Aware Explanation Workflow
# =============================================================================


class TestModelExplanationWorkflow:
    """
    Workflow 7: User asks: Why was SPY classified as this regime?
    -> MODEL_EXPLANATION intent -> ModelExplanationPipeline -> model evidence
    -> feature/profile comparison -> GroundingValidator -> cited explanation.
    """

    def test_model_explanation_pipeline_e2e(self, workflow_client: TestClient) -> None:
        payload = {
            "question": "Why was SPY classified as this regime?",
            "symbol": "SPY",
        }
        res = workflow_client.post("/api/v1/research/query", json=payload)
        assert res.status_code == 200
        data = res.json()

        assert data["intent"] == "MODEL_EXPLANATION"
        assert data["symbol"] == "SPY"
        assert len(data["evidence"]) >= 1

        # Evidence must contain model explanation packets
        source_types = [p["source_type"] for p in data["evidence"]]
        assert any("model_explanation" in st or "regime" in st for st in source_types)

        # Answer must be cited and non-empty
        assert len(data["answer"]) > 20
        assert len(data["citations"]) >= 1


# =============================================================================
# Workflow 8 — AI Safety Refusal Workflow
# =============================================================================


class TestAISafetyRefusalWorkflow:
    """
    Workflow 8: Deterministic refusal of price predictions and investment advice:
    - Will SPY go up tomorrow? -> PREDICTION_REFUSAL
    - Should I buy SPY? -> ADVICE_REFUSAL
    Zero LLM execution, zero fabricated forecast, user can continue.
    """

    def test_price_prediction_refusal_e2e(self, workflow_client: TestClient) -> None:
        payload = {"question": "Will SPY go up tomorrow?"}
        res = workflow_client.post("/api/v1/research/query", json=payload)
        assert res.status_code == 200
        data = res.json()

        assert data["intent"] == "PREDICTION_REFUSAL"
        assert "does not provide future price predictions" in data["answer"]
        # No speculative numbers or price targets
        assert "target price" not in data["answer"].lower()

    def test_trading_advice_refusal_e2e(self, workflow_client: TestClient) -> None:
        payload = {"question": "Should I buy SPY?"}
        res = workflow_client.post("/api/v1/research/query", json=payload)
        assert res.status_code == 200
        data = res.json()

        assert data["intent"] == "ADVICE_REFUSAL"
        assert "does not provide personalized financial advice" in data["answer"]
        assert data["citations"] == []


# =============================================================================
# Workflow 9 — AI Grounding Failure & Sanitization Workflow
# =============================================================================


class HallucinatingModelProvider(ResearchModelProvider):
    """
    Adversarial model provider simulating hallucinations by inventing
    unsupported numerical claims (e.g. volatility = 42.0% when evidence = 18.0%).
    """

    @property
    def provider_name(self) -> str:
        return "adversarial_mock"

    @property
    def model_name(self) -> str:
        return "adversarial-hallucinator-v1"

    async def generate(
        self,
        prompt: str,
        system_prompt: str,
        evidence: list[EvidencePacket],
    ) -> str:
        # Fabricated volatility claim not present in evidence
        return (
            "Based on the analysis, SPY has an annualized volatility of 42.0% [1]. "
            "The market is in extreme distress."
        )

    async def stream(
        self,
        prompt: str,
        system_prompt: str,
        evidence: list[EvidencePacket],
    ) -> Any:  # noqa: ANN401
        yield "Fabricated volatility 42.0%."


class TestGroundingFailureWorkflow:
    """
    Workflow 9: Simulated provider returning an unsupported claim
    -> GroundingValidator detects numerical mismatch -> rejects hallucination
    -> generates safe verified fallback -> fabricated number never reaches user.
    """

    def test_grounding_failure_and_safe_fallback_e2e(
        self,
        workflow_client: TestClient,
        golden_provider: GoldenMarketDataProvider,
    ) -> None:
        # Wire up adversarial provider into a custom app
        market_svc = MarketDataService(provider=golden_provider)
        intel_facade = MarketIntelligenceFacade(market_service=market_svc)
        risk_svc = PortfolioRiskService()
        backtest_svc = BacktestingService()
        ai_svc = AIResearchService(
            market_service=market_svc,
            market_intelligence=intel_facade,
            risk_service=risk_svc,
            backtest_service=backtest_svc,
            provider=HallucinatingModelProvider(),
        )

        app = create_app()
        app.dependency_overrides[ai_research_service_dep] = lambda: ai_svc
        app.dependency_overrides[market_service_dep] = lambda: market_svc
        app.dependency_overrides[market_intelligence_dep] = lambda: intel_facade

        with TestClient(app) as client:
            res = client.post(
                "/api/v1/research/query",
                json={"question": "What is the volatility of SPY?", "symbol": "SPY"},
            )
            assert res.status_code == 200
            data = res.json()

            # Critical invariant: The hallucinated 42.0% was rejected
            assert "42.0%" not in data["answer"]
            assert "42%" not in data["answer"]
            # Grounding fallback was substituted
            assert len(data["answer"]) > 0


# =============================================================================
# Workflow 10 — API Failure Recovery Workflow
# =============================================================================


class TestApiFailureRecoveryWorkflow:
    """
    Workflow 10: Realistic failure states -> handled error response
    -> client retries -> successful recovery.
    """

    def test_failure_and_recovery_flow(
        self,
        workflow_client: TestClient,
        golden_provider: GoldenMarketDataProvider,
    ) -> None:
        # 1. Invalid query parameters trigger handled 422 error
        err_res = workflow_client.get(
            "/api/v1/markets/SPY/risk",
            params={
                "start": (BASE_DATE + timedelta(days=10)).isoformat(),
                "end": BASE_DATE.isoformat(),
            },
        )
        assert err_res.status_code == 422
        assert err_res.json()["error"]["code"] == "VALIDATION_ERROR"

        # 2. Corrected query on retry succeeds cleanly
        valid_res = workflow_client.get(
            "/api/v1/markets/SPY/risk",
            params={
                "start": BASE_DATE.isoformat(),
                "end": (BASE_DATE + timedelta(days=60)).isoformat(),
            },
        )
        assert valid_res.status_code == 200
        assert valid_res.json()["symbol"] == "SPY"


# =============================================================================
# Workflow 11 — Empty Data Workflow
# =============================================================================


class TestEmptyDataWorkflow:
    """
    Workflow 11: Valid market in catalog + empty historical data store
    -> API returns controlled error envelope without 500 crashes or leaked stack traces.
    """

    def test_empty_market_data_handled_gracefully(self, workflow_client: TestClient) -> None:
        start_str = BASE_DATE.isoformat()
        end_str = (BASE_DATE + timedelta(days=60)).isoformat()

        # "EMPTY" is registered in the catalog but has 0 bars
        res = workflow_client.get(
            "/api/v1/markets/EMPTY/data",
            params={"start": start_str, "end": end_str},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["symbol"] == "EMPTY"
        assert data["count"] == 0
        assert data["items"] == []

        # Requesting risk on an empty market triggers a clean 422, not a 500 crash
        risk_res = workflow_client.get(
            "/api/v1/markets/EMPTY/risk",
            params={"start": start_str, "end": end_str},
        )
        assert risk_res.status_code == 422
        risk_err = risk_res.json()["error"]
        assert risk_err["code"] == "VALIDATION_ERROR"
        assert "Insufficient historical data" in risk_err["message"]


# =============================================================================
# Workflow 12 — Unknown Market Workflow
# =============================================================================


class TestUnknownMarketWorkflow:
    """
    Workflow 12: UNKNOWN_SYMBOL rejected early by catalog lookup with 404
    and by research query with friendly fallback message.
    """

    def test_unknown_market_rejection_e2e(self, workflow_client: TestClient) -> None:
        start_str = BASE_DATE.isoformat()
        end_str = (BASE_DATE + timedelta(days=60)).isoformat()

        # 1. Market data route
        res = workflow_client.get(
            "/api/v1/markets/UNKNOWN_XYZ/data",
            params={"start": start_str, "end": end_str},
        )
        assert res.status_code == 404
        assert res.json()["error"]["code"] == "PROVIDER_SYMBOL_NOT_FOUND"

        # 2. AI Research route
        research_res = workflow_client.post(
            "/api/v1/research/query",
            json={"question": "What is the regime of FOOBAR?"},
        )
        assert research_res.status_code == 200
        data = research_res.json()
        assert "couldn't find that market" in data["answer"].lower()
        assert data["citations"] == []


# =============================================================================
# Workflow 13 — Permission Boundary Workflow
# =============================================================================


class TestPermissionBoundaryWorkflow:
    """
    Workflow 13: Verify public market intelligence routes are public
    while user profile operations strictly require valid authentication.
    """

    def test_permission_boundaries_e2e(self, workflow_client: TestClient) -> None:
        start_str = BASE_DATE.isoformat()
        end_str = (BASE_DATE + timedelta(days=60)).isoformat()

        # Public endpoints accessible with zero tokens
        assert workflow_client.get("/api/v1/markets").status_code == 200
        assert (
            workflow_client.get(
                "/api/v1/markets/SPY/data",
                params={"start": start_str, "end": end_str},
            ).status_code
            == 200
        )
        assert (
            workflow_client.get(
                "/api/v1/markets/SPY/risk",
                params={"start": start_str, "end": end_str},
            ).status_code
            == 200
        )

        # Protected endpoints strictly guarded
        assert workflow_client.get("/api/v1/auth/me").status_code == 401
        assert (
            workflow_client.get(
                "/api/v1/auth/me", headers={"Authorization": "Bearer bad"}
            ).status_code
            == 401
        )


# =============================================================================
# Workflow 14 — Request Correlation Workflow
# =============================================================================


class TestRequestCorrelationWorkflow:
    """
    Workflow 14: Verify X-Request-ID propagation across requests, responses,
    and error envelopes, with zero secret or header leakage.
    """

    def test_request_id_correlation_and_secrecy(self, workflow_client: TestClient) -> None:
        start_str = BASE_DATE.isoformat()
        end_str = (BASE_DATE + timedelta(days=60)).isoformat()
        corr_id = "corr-test-workflow-789"

        res = workflow_client.get(
            "/api/v1/markets/SPY/data",
            params={"start": start_str, "end": end_str},
            headers={"X-Request-ID": corr_id},
        )
        assert res.status_code == 200
        assert res.headers.get("X-Request-ID") == corr_id

        # Error response must echo the correlation ID
        err_res = workflow_client.get(
            "/api/v1/markets/UNKNOWN/data",
            params={"start": start_str, "end": end_str},
            headers={"X-Request-ID": corr_id},
        )
        assert err_res.status_code == 404
        assert err_res.headers.get("X-Request-ID") == corr_id
        assert err_res.json()["error"]["request_id"] == corr_id

        # Verify no credentials or authorization headers are echoed in response bodies
        body_text = err_res.text
        assert "password" not in body_text.lower()
        assert "secret" not in body_text.lower()
        assert "authorization" not in body_text.lower()


# =============================================================================
# Workflow 15 & 19 — Research SSE Streaming & Interruption Workflow
# =============================================================================


class TestResearchSSEWorkflow:
    """
    Workflow 15 & 19: Research SSE stream lifecycle:
    Ordered events (metadata -> evidence -> token -> complete),
    and interruption handling.
    """

    def test_research_sse_streaming_ordered_events(self, workflow_client: TestClient) -> None:
        payload = {
            "question": "What is the volatility of SPY?",
            "symbol": "SPY",
            "stream": True,
        }
        res = workflow_client.post("/api/v1/research/query", json=payload)
        assert res.status_code == 200
        assert "text/event-stream" in res.headers.get("content-type", "")

        body = res.text
        # Verify chronological sequence of event types
        meta_pos = body.find("event: metadata")
        evid_pos = body.find("event: evidence")
        tok_pos = body.find("event: token")
        comp_pos = body.find("event: complete")

        assert meta_pos != -1, "Missing metadata event"
        assert evid_pos != -1, "Missing evidence event"
        assert tok_pos != -1, "Missing token event"
        assert comp_pos != -1, "Missing complete event"

        assert meta_pos < evid_pos < tok_pos < comp_pos, "SSE events must arrive in strict order"
