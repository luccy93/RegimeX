"""
RegimeX AI Research — Grounding Engine & Prompt Construction
============================================================
Translates structured EvidencePackets into controlled prompt contexts and builds
1-to-1 citations. Enforces the 10 core grounding invariants.
"""

from __future__ import annotations

import json
from typing import Any

from app.modules.ai_research.domain.models import Citation, EvidencePacket

SYSTEM_PROMPT = """You are the RegimeX AI Quantitative Market Research Assistant.
Your primary objective is to explain market regime dynamics, risk profiles, and backtesting
metrics using ONLY the verified evidence packets supplied by the RegimeX platform.

Core Operating Principles:
1. Grounding Invariant: Answer ONLY from the supplied RegimeX evidence. Never invent facts.
2. No Missing Values: If a metric is null or missing, explicitly state it is unavailable.
3. Strict Citations: Cite every factual assertion using square brackets, e.g. [1], [2].
4. Epistemic Separation: Distinguish observed data from model outputs and interpretations.
5. Uncertainty & Limitations: Explicitly state confidence levels, sample sizes, and bounds.
6. Absolute Prohibition on Advice: NEVER provide financial advice, allocations, or signals.
7. Absolute Prohibition on Prediction: NEVER forecast future prices or future regime switches.
8. Bounded Access: Never claim access to live feeds or data outside supplied evidence packets.
9. Numerical Integrity: Preserve numbers, percentages, and metrics exactly as provided.
10. Quantitative Tone: Maintain an objective, institutional, and research-focused tone.
"""


class GroundingEngine:
    """
    Constructs grounded prompt contexts and generates explicit citations.
    """

    @classmethod
    def build_system_prompt(cls) -> str:
        return SYSTEM_PROMPT.strip()

    @classmethod
    def build_user_prompt(
        cls,
        question: str,
        evidence: list[EvidencePacket],
        symbol: str | None = None,
    ) -> str:
        """
        Construct structured user prompt containing question and numbered evidence packets.
        """
        lines: list[str] = [
            f"User Question: {question.strip()}",
            "",
            "=== Supplied RegimeX Evidence Packets ===",
        ]

        if not evidence:
            lines.append("No specific evidence packets available.")
        else:
            for idx, packet in enumerate(evidence, start=1):
                lines.append(f"[{idx}] Source ID: {packet.source_id}")
                lines.append(f"    Type: {packet.source_type}")
                lines.append(f"    Title: {packet.title}")
                if packet.timestamp:
                    lines.append(f"    Timestamp: {packet.timestamp}")
                facts_str = json.dumps(packet.facts, indent=2, sort_keys=True)
                lines.append("    Verified Facts:")
                for fact_line in facts_str.splitlines():
                    lines.append(f"      {fact_line}")
                lines.append("")

        lines.extend(
            [
                "=== Instructions ===",
                "Provide a clear, grounded response to the question using the evidence above.",
                "Every factual statement must include its citation marker (e.g. [1]).",
                "Do not speculate or extrapolate beyond the provided facts.",
            ]
        )
        return "\n".join(lines)

    @classmethod
    def build_citations(cls, evidence: list[EvidencePacket]) -> list[Citation]:
        """
        Generate Citation entities corresponding to each numbered evidence packet.
        """
        citations: list[Citation] = []
        for idx, packet in enumerate(evidence, start=1):
            symbol = packet.facts.get("symbol") if isinstance(packet.facts, dict) else None
            model_info = packet.metadata.get("model_name") or packet.facts.get("model_name")

            # Create concise summary of top facts
            summary_parts: list[str] = []
            for k, v in list(packet.facts.items())[:4]:
                if isinstance(v, (int, float, str, bool)):
                    summary_parts.append(f"{k}: {v}")
            summary_str = ", ".join(summary_parts) if summary_parts else None

            details_dict: dict[str, Any] = {
                "source_id": packet.source_id,
                "source_type": packet.source_type,
                "facts": packet.facts,
                "metadata": packet.metadata,
            }

            citations.append(
                Citation(
                    id=idx,
                    source_id=packet.source_id,
                    source_type=packet.source_type,
                    title=packet.title,
                    symbol=str(symbol) if symbol else None,
                    timestamp=packet.timestamp,
                    model=str(model_info) if model_info else None,
                    facts_summary=summary_str,
                    details=details_dict,
                )
            )
        return citations
