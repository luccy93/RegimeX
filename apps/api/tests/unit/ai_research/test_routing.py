"""
RegimeX AI Research — Intent Routing Tests
==========================================
Verifies deterministic classification of analytical scopes and immediate safety refusals.
"""

from __future__ import annotations

import pytest
from app.modules.ai_research.application.routing import IntentRouter
from app.modules.ai_research.domain.models import ResearchIntent


class TestIntentRouting:
    """Test deterministic regex and rule routing."""

    @pytest.mark.parametrize(
        ("question", "expected"),
        [
            ("Will SPY rise tomorrow?", ResearchIntent.PREDICTION_REFUSAL),
            ("What stock will go up?", ResearchIntent.PREDICTION_REFUSAL),
            ("Will the regime turn bearish next week?", ResearchIntent.PREDICTION_REFUSAL),
            ("Give me a price prediction for SPY", ResearchIntent.PREDICTION_REFUSAL),
            ("Where will QQQ trade next month?", ResearchIntent.PREDICTION_REFUSAL),
            ("Should I buy SPY right now?", ResearchIntent.ADVICE_REFUSAL),
            ("Is it a good time to sell AAPL?", ResearchIntent.ADVICE_REFUSAL),
            ("Give me a buy signal for MSFT", ResearchIntent.ADVICE_REFUSAL),
            ("What regime is SPY currently in?", ResearchIntent.CURRENT_REGIME),
            ("How long has the current regime lasted?", ResearchIntent.CURRENT_REGIME),
            ("What is the current regime confidence?", ResearchIntent.CURRENT_REGIME),
            ("How frequently has SPY transitioned between regimes?", ResearchIntent.TRANSITIONS),
            ("What does the transition matrix show?", ResearchIntent.TRANSITIONS),
            ("What is the regime persistence probability?", ResearchIntent.TRANSITIONS),
            (
                "What are the historical characteristics of this regime?",
                ResearchIntent.REGIME_ANALYTICS,
            ),
            ("Show me the regime profile distributions", ResearchIntent.REGIME_ANALYTICS),
            ("What is the current volatility of SPY?", ResearchIntent.RISK),
            ("What was the maximum drawdown during this period?", ResearchIntent.RISK),
            ("What is the 95% Value at Risk?", ResearchIntent.RISK),
            ("Explain the latest backtest results.", ResearchIntent.BACKTEST),
            ("What was the strategy win rate in backtesting?", ResearchIntent.BACKTEST),
            ("What assumptions were used in this backtest?", ResearchIntent.METHODOLOGY),
            ("How is the regime detection calculated?", ResearchIntent.METHODOLOGY),
            (
                "Compare the current regime with historical regime profiles.",
                ResearchIntent.COMPARISON,
            ),
            ("Tell me about SPY", ResearchIntent.MARKET_OVERVIEW),
            ("What is the weather in London today?", ResearchIntent.UNSUPPORTED),
        ],
    )
    def test_intent_classification(self, question: str, expected: ResearchIntent) -> None:
        classified = IntentRouter.classify(question)
        assert classified == expected
