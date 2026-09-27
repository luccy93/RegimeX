"""
RegimeX AI Research — Grounding Validator & Safety Enforcement
==============================================================
Validates generated responses against supplied evidence packets before returning.
Enforces numerical integrity, citation traceability, and safety boundary constraints
(no price predictions, no trade recommendations, no invented metrics).
"""

from __future__ import annotations

import re

from app.modules.ai_research.domain.models import EvidencePacket, ResearchIntent

PROHIBITED_RECOMMENDATION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(you should|i recommend|we recommend)\s+(buy|sell|short|hold|trade)\b", re.I),
    re.compile(r"\b(strong buy|strong sell|buy signal|sell signal)\b", re.I),
    re.compile(r"\b(target price of|price target of|guaranteed return)\b", re.I),
    re.compile(r"\b(will reach \$?\d+|will surge to|will drop to)\b", re.I),
)

CITATION_TAG_PATTERN = re.compile(r"\[(\d+)\]")
NUMERIC_PATTERN = re.compile(r"(?<![a-zA-Z])(?:\$)?(\d+(?:\.\d+)?%?)(?![a-zA-Z])")


class GroundingValidator:
    """
    Validates assistant answers against grounding rules and safety constraints.
    """

    @classmethod
    def validate(
        cls,
        answer: str,
        evidence: list[EvidencePacket],
        intent: ResearchIntent,
        symbol: str | None = None,
    ) -> tuple[bool, str, list[int]]:
        """
        Validate the generated answer.

        Returns:
            (is_valid, sanitized_or_fallback_answer, cited_indices)
        """
        # 1. Immediate Refusals for Prediction, Advice, and Unsupported Queries
        if intent == ResearchIntent.PREDICTION_REFUSAL:
            refusal_msg = (
                "RegimeX can describe historical and model-derived regime information and "
                "risk analytics, but it does not provide future price predictions or "
                "speculative forecasts."
            )
            if symbol and evidence:
                context_add = f"\n\nBased on historical observations for {symbol}: [1]"
                for p in evidence:
                    if p.source_type == "regime":
                        cur_label = p.facts.get("current_regime_label", "UNKNOWN")
                        conf = p.facts.get("confidence")
                        conf_str = f" with {conf * 100:.1f}% confidence" if conf else ""
                        context_add += f"\n- Current regime is classified as {cur_label}{conf_str}."
                    elif p.source_type == "risk":
                        vol = p.facts.get("annualized_volatility")
                        if vol is not None:
                            context_add += (
                                f"\n- Annualized realized volatility is {vol * 100:.1f}%."
                            )
                return True, refusal_msg + context_add, [1]
            return True, refusal_msg, []

        if intent == ResearchIntent.ADVICE_REFUSAL:
            refusal_msg = (
                "RegimeX is a quantitative research platform and does not provide personalized "
                "financial advice, trade signals, or buy/sell recommendations."
            )
            return True, refusal_msg, []

        if intent == ResearchIntent.UNSUPPORTED:
            return (
                True,
                (
                    "This question is outside the scope of RegimeX market research analytics. "
                    "You can ask about current market regimes, transition probabilities, "
                    "portfolio risk, drawdown metrics, and historical backtests."
                ),
                [],
            )

        clean_answer = answer.strip()
        if not clean_answer:
            return False, cls.generate_grounded_fallback(evidence, intent, symbol), []

        # 2. Check for Prohibited Recommendation Language
        for pattern in PROHIBITED_RECOMMENDATION_PATTERNS:
            if pattern.search(clean_answer):
                # Detected advice/recommendation violation — fall back immediately
                return False, cls.generate_grounded_fallback(evidence, intent, symbol), []

        # 3. Citation Extraction & Traceability Check
        found_citations = [int(m.group(1)) for m in CITATION_TAG_PATTERN.finditer(clean_answer)]
        valid_indices = set(range(1, len(evidence) + 1))

        # Every cited index must be valid
        if any(idx not in valid_indices for idx in found_citations):
            return False, cls.generate_grounded_fallback(evidence, intent, symbol), []

        # Factual domain queries require at least one valid citation
        if evidence and not found_citations:
            # If model forgot citations, generate verified grounded fallback
            return False, cls.generate_grounded_fallback(evidence, intent, symbol), []

        # 4. Numerical Integrity Check (adversarial prompt injection defense)
        if not cls._verify_numerical_integrity(clean_answer, evidence):
            return False, cls.generate_grounded_fallback(evidence, intent, symbol), []

        return True, clean_answer, sorted(set(found_citations))

    @classmethod
    def _verify_numerical_integrity(cls, answer: str, evidence: list[EvidencePacket]) -> bool:
        """
        Check that numbers appearing in the answer match known evidence facts.
        """
        # Collect all numerical values from evidence facts
        allowed_numbers: set[float] = set()

        def extract_nums(val: object) -> None:
            if isinstance(val, (int, float)) and not isinstance(val, bool):
                fval = float(val)
                allowed_numbers.add(round(fval, 2))
                allowed_numbers.add(round(fval * 100, 1))  # percentage
                allowed_numbers.add(round(fval * 100, 2))
                allowed_numbers.add(round(fval, 4))
            elif isinstance(val, dict):
                for v in val.values():
                    extract_nums(v)
            elif isinstance(val, (list, tuple)):
                for item in val:
                    extract_nums(item)

        for p in evidence:
            extract_nums(p.facts)

        # If answer mentions specific key analytics terms with arbitrary numbers, verify
        for metric_kw in ("volatility", "drawdown", "confidence", "var", "win rate"):
            if metric_kw in answer.lower():
                # Extract number following keyword
                m = re.search(rf"{metric_kw}[^0-9\n]{{1,20}}(\d+(?:\.\d+)?)%?", answer, re.I)
                if m:
                    val = float(m.group(1))
                    # Check if val or val/100 matches any allowed number
                    matched = any(
                        abs(val - allowed) < 0.2 or abs((val / 100.0) - allowed) < 0.005
                        for allowed in allowed_numbers
                    )
                    # If this key metric has numbers in evidence, it must be supported
                    if allowed_numbers and not matched:
                        # Value was fabricated or injected
                        return False

        return True

    @classmethod
    def generate_grounded_fallback(
        cls,
        evidence: list[EvidencePacket],
        intent: ResearchIntent,
        symbol: str | None = None,
    ) -> str:
        """
        Construct a deterministic, 100% verified grounded answer directly from evidence packets.
        """
        sym = symbol or "the analyzed instrument"
        parts: list[str] = []

        citation_idx_map: dict[str, int] = {
            p.source_id: idx for idx, p in enumerate(evidence, start=1)
        }

        # Find packets
        regime_packet = next((p for p in evidence if p.source_type == "regime"), None)
        transition_packet = next(
            (p for p in evidence if p.source_type == "regime_transition"), None
        )
        risk_packet = next((p for p in evidence if p.source_type == "risk"), None)
        backtest_packet = next((p for p in evidence if p.source_type == "backtest"), None)
        market_packet = next((p for p in evidence if p.source_type == "market"), None)

        if intent == ResearchIntent.CURRENT_REGIME and regime_packet:
            c_idx = citation_idx_map.get(regime_packet.source_id, 1)
            facts = regime_packet.facts
            cur_label = facts.get("current_regime_label", "UNKNOWN")
            conf = facts.get("confidence")
            conf_str = f"{conf * 100:.1f}%" if conf is not None else "unavailable"
            dur = facts.get("observations_in_current_run", 1)
            avg_dur = facts.get("historical_average_duration", 0.0)
            parts.append(
                f"Based on RegimeX model analytics, {sym} is currently classified in the "
                f"**{cur_label}** regime with **{conf_str}** model confidence [{c_idx}]."
            )
            parts.append(
                f"The current regime run has persisted for **{dur}** consecutive observations, "
                f"compared to a historical average duration of **{avg_dur}** periods "
                f"for this state [{c_idx}]."
            )

        elif intent == ResearchIntent.TRANSITIONS and transition_packet:
            c_idx = citation_idx_map.get(transition_packet.source_id, 1)
            facts = transition_packet.facts
            pers = facts.get("global_persistence_rate")
            pers_str = f"{pers * 100:.1f}%" if pers is not None else "N/A"
            chg = facts.get("global_change_rate")
            chg_str = f"{chg * 100:.1f}%" if chg is not None else "N/A"
            parts.append(
                f"Empirical regime transition dynamics for {sym} show a global regime persistence "
                f"rate of **{pers_str}** and a regime change rate of **{chg_str}** [{c_idx}]."
            )
            # Find current regime transition facts if present
            for k, v in facts.items():
                if isinstance(v, dict) and "persistence_probability" in v:
                    state_name = k.replace("_analytics", "").replace("regime_", "")
                    p_prob = v.get("persistence_probability", 0.0)
                    dest = v.get("most_likely_destination", "N/A")
                    parts.append(
                        f"State {state_name} has a **{p_prob * 100:.1f}%** 1-step persistence "
                        f"probability, with its most likely destination being "
                        f"state **{dest}** [{c_idx}]."
                    )
                    break

        elif intent == ResearchIntent.RISK and risk_packet:
            c_idx = citation_idx_map.get(risk_packet.source_id, 1)
            facts = risk_packet.facts
            vol = facts.get("annualized_volatility")
            vol_str = f"{vol * 100:.2f}%" if vol is not None else "N/A"
            mdd = facts.get("max_drawdown")
            mdd_str = f"{mdd * 100:.2f}%" if mdd is not None else "N/A"
            var = facts.get("var_95")
            var_str = f"{var * 100:.2f}%" if var is not None else "N/A"
            es = facts.get("expected_shortfall_95")
            es_str = f"{es * 100:.2f}%" if es is not None else "N/A"
            parts.append(
                f"Historical portfolio risk analysis for {sym} indicates an annualized "
                f"volatility of **{vol_str}** and a maximum historical drawdown of "
                f"**{mdd_str}** [{c_idx}]."
            )
            parts.append(
                f"At the 95% confidence level, the parametric Value at Risk (VaR 95%) is "
                f"**{var_str}**, and Expected Shortfall (CVaR 95%) is **{es_str}** [{c_idx}]."
            )

        elif intent == ResearchIntent.BACKTEST and backtest_packet:
            c_idx = citation_idx_map.get(backtest_packet.source_id, 1)
            facts = backtest_packet.facts
            strat = facts.get("strategy_name", "Strategy")
            tot_ret = facts.get("total_return")
            ret_str = f"{tot_ret * 100:.2f}%" if tot_ret is not None else "N/A"
            trades = facts.get("completed_trades", 0)
            win_rate = facts.get("win_rate", 0.0)
            mdd = facts.get("max_drawdown", 0.0)
            parts.append(
                f"Systematic backtest simulation for {sym} under the **{strat}** strategy "
                f"yielded a total return of **{ret_str}** over the simulated period [{c_idx}]."
            )
            parts.append(
                f"Execution summary: **{trades}** completed trades with a win rate of "
                f"**{win_rate * 100:.1f}%**, and maximum simulated drawdown of "
                f"**{mdd * 100:.2f}%** [{c_idx}]."
            )

        elif market_packet:
            c_idx = citation_idx_map.get(market_packet.source_id, 1)
            facts = market_packet.facts
            desc = facts.get("description", sym)
            exch = facts.get("exchange", "Unknown")
            close = facts.get("latest_close")
            close_str = f"${close:.2f}" if close is not None else "N/A"
            parts.append(
                f"**{sym}** ({desc}) is traded on **{exch}** with a latest observed "
                f"closing price of **{close_str}** [{c_idx}]."
            )

        if not parts:
            parts.append(
                f"Quantitative analytics for {sym} are available across regime intelligence, "
                f"portfolio risk, and systematic backtesting [1]."
            )

        return "\n\n".join(parts)
