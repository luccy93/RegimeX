"""
RegimeX AI Research — Deterministic Intent Routing
==================================================
Rule-driven intent classifier that maps user questions to analytical scopes.
Does not use an LLM for classification, ensuring zero-latency, 100% deterministic
routing and immediate refusal of predictive or investment-advice queries.
"""

from __future__ import annotations

import re

from app.modules.ai_research.domain.models import ResearchIntent

# Refusal triggers for future price predictions or forecasts
PREDICTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\bwill\s+[a-zA-Z0-9\-_.]+\s+"
        r"(rise|fall|drop|go up|go down|increase|decrease|rally|crash|surge)\b",
        re.I,
    ),
    re.compile(r"\b(what stock|which stock|which asset)\s+will\s+go up\b", re.I),
    re.compile(
        r"\bwill\s+(the\s+)?regime\s+(turn|switch|change|become)\s+(bullish|bearish|neutral)\b",
        re.I,
    ),
    re.compile(r"\b(price prediction|forecast|target price|tomorrow|next week|next month)\b", re.I),
    re.compile(r"\bwhere will\s+[a-zA-Z0-9\-_.]+\s+(be|trade)\b", re.I),
)

# Refusal triggers for personalized financial or trading advice
ADVICE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bshould I (buy|sell|short|hold|trade|enter|exit)\b", re.I),
    re.compile(r"\bis it a good time to (buy|sell|short|hold)\b", re.I),
    re.compile(
        r"\b(give me|what is)\s+(a\s+)?(trading advice|financial advice|buy signal|sell signal)\b",
        re.I,
    ),
    re.compile(r"\b(recommend|recommendation)\s+(a\s+)?(trade|stock|asset|position)\b", re.I),
)

# Analytical topic patterns
CURRENT_REGIME_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(what|current|active)\s+regime\b", re.I),
    re.compile(r"\bwhat regime is\s+[a-zA-Z0-9\-_.]+\s+(currently\s+)?in\b", re.I),
    re.compile(r"\bhow long has (the\s+)?current regime lasted\b", re.I),
    re.compile(r"\bregime duration\b", re.I),
    re.compile(r"\b(current\s+)?regime confidence\b", re.I),
    re.compile(r"\bhow long (has\s+it\s+been|in current run)\b", re.I),
)

TRANSITIONS_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\btransition(s)?\b", re.I),
    re.compile(r"\btransition matrix\b", re.I),
    re.compile(r"\bpersistence(\s+probability)?\b", re.I),
    re.compile(r"\bchange rate\b", re.I),
    re.compile(r"\bdestination(s)?\b", re.I),
    re.compile(r"\bswitch(es|ed|ing)? between regimes\b", re.I),
    re.compile(r"\bhow frequently has\s+[a-zA-Z0-9\-_.]+\s+transitioned\b", re.I),
    re.compile(r"\btransition entropy\b", re.I),
)

REGIME_ANALYTICS_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(historical\s+)?characteristic(s)?\b", re.I),
    re.compile(r"\bregime profile(s)?\b", re.I),
    re.compile(r"\bfeature (distribution|statistics|values)\b", re.I),
    re.compile(r"\bregime distribution\b", re.I),
    re.compile(r"\bhow often does\s+[a-zA-Z0-9\-_.]+\s+stay in\b", re.I),
    re.compile(r"\bhistorical regime\b", re.I),
)

RISK_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(current\s+)?volatility\b", re.I),
    re.compile(r"\b(maximum\s+)?drawdown\b", re.I),
    re.compile(r"\bvar\b", re.I),
    re.compile(r"\bvalue at risk\b", re.I),
    re.compile(r"\bexpected shortfall\b", re.I),
    re.compile(r"\bcvar\b", re.I),
    re.compile(r"\bdownside deviation\b", re.I),
    re.compile(r"\brisk profile\b", re.I),
    re.compile(r"\bwhat happened to\s+[a-zA-Z0-9\-_.]+'s risk\b", re.I),
)

BACKTEST_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bbacktest(ing)?\b", re.I),
    re.compile(r"\bstrategy\b", re.I),
    re.compile(r"\bequity\b", re.I),
    re.compile(r"\bpnl\b", re.I),
    re.compile(r"\bprofit and loss\b", re.I),
    re.compile(r"\bwin rate\b", re.I),
    re.compile(r"\btrades\b", re.I),
    re.compile(r"\bbuy and hold\b", re.I),
    re.compile(r"\bregime adaptive\b", re.I),
    re.compile(r"\bperformance report\b", re.I),
    re.compile(r"\bexplain the (latest\s+)?backtest\b", re.I),
)

METHODOLOGY_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bassumption(s)?\b", re.I),
    re.compile(r"\bmethodology\b", re.I),
    re.compile(r"\bhow is\s+.+?\s+calculated\b", re.I),
    re.compile(r"\bwhat does\s+(?:the\s+)?.+?\s+mean\b", re.I),
    re.compile(r"\bmetric definition\b", re.I),
    re.compile(r"\blimitation(s)?\b", re.I),
)

COMPARISON_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bcompare\b", re.I),
    re.compile(r"\bcomparison\b", re.I),
    re.compile(r"\bdifference between\b", re.I),
    re.compile(r"\bversus\b", re.I),
    re.compile(r"\bvs\b", re.I),
)

MARKET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bmarket(s)?\b", re.I),
    re.compile(r"\btell me about\s+[a-zA-Z0-9\-_.]+\b", re.I),
    re.compile(r"\boverview\b", re.I),
    re.compile(r"\bprice\b", re.I),
    re.compile(r"\bbar(s)?\b", re.I),
    re.compile(r"\bohlcv\b", re.I),
)

MODEL_EXPLANATION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bwhy\s+(is|was|did)\s+.+?\s+(classified|assigned|labeled|detected)\b", re.I),
    re.compile(r"\bhow did (the\s+)?model\s+(decide|determine|classify|assign|detect)\b", re.I),
    re.compile(r"\bexplain (the\s+)?(classification|assignment|regime detection)\b", re.I),
    re.compile(r"\bwhat (features?|inputs?|factors?)\s+(drove|caused|led to|contributed)\b", re.I),
    re.compile(r"\bmodel (explanation|reasoning|logic|basis|confidence)\b", re.I),
    re.compile(r"\bwhy (this|that) regime\b", re.I),
    re.compile(r"\bwhat made (the\s+)?model\b", re.I),
    re.compile(r"\bhow (confident|certain|sure) is the model\b", re.I),
    re.compile(r"\bexplain (the\s+)?confidence\b", re.I),
    re.compile(r"\bfeature (importance|contribution|impact)\b", re.I),
    re.compile(r"\bwhy not\s+.+?\s+regime\b", re.I),
    re.compile(r"\bwhat (algorithm|model)\s+(is|was)\s+(used|applied|running)\b", re.I),
    re.compile(r"\bmodel (provenance|version|metadata)\b", re.I),
)


class IntentRouter:
    """
    Classifies user questions into deterministic analytical scopes.
    """

    @classmethod
    def classify(cls, question: str) -> ResearchIntent:
        """
        Classify question intent via ordered rule evaluation.
        Evaluates safety and refusal constraints prior to domain routing.
        """
        clean_q = question.strip()

        # 1. Safety Refusal Checks
        for pattern in PREDICTION_PATTERNS:
            if pattern.search(clean_q):
                return ResearchIntent.PREDICTION_REFUSAL

        for pattern in ADVICE_PATTERNS:
            if pattern.search(clean_q):
                return ResearchIntent.ADVICE_REFUSAL

        # 2. Model-Aware Explanation Queries
        for pattern in MODEL_EXPLANATION_PATTERNS:
            if pattern.search(clean_q):
                return ResearchIntent.MODEL_EXPLANATION

        # 3. Methodology & Model Assumptions (e.g. assumptions in backtests)
        for pattern in METHODOLOGY_PATTERNS:
            if pattern.search(clean_q):
                return ResearchIntent.METHODOLOGY

        # 3. Comparison Check (if comparing regimes or strategies)
        for pattern in COMPARISON_PATTERNS:
            if pattern.search(clean_q):
                return ResearchIntent.COMPARISON

        # 4. Transitions & Markov Analytics
        for pattern in TRANSITIONS_PATTERNS:
            if pattern.search(clean_q):
                return ResearchIntent.TRANSITIONS

        # 5. Current Regime & Duration
        for pattern in CURRENT_REGIME_PATTERNS:
            if pattern.search(clean_q):
                return ResearchIntent.CURRENT_REGIME

        # 6. Historical Regime Profiles & Features
        for pattern in REGIME_ANALYTICS_PATTERNS:
            if pattern.search(clean_q):
                return ResearchIntent.REGIME_ANALYTICS

        # 7. Risk, Volatility, Drawdowns
        for pattern in RISK_PATTERNS:
            if pattern.search(clean_q):
                return ResearchIntent.RISK

        # 8. Backtesting & Execution
        for pattern in BACKTEST_PATTERNS:
            if pattern.search(clean_q):
                return ResearchIntent.BACKTEST

        # 9. Market Overview
        for pattern in MARKET_PATTERNS:
            if pattern.search(clean_q):
                return ResearchIntent.MARKET_OVERVIEW

        # 10. Fallback / General / Unsupported
        return ResearchIntent.UNSUPPORTED
