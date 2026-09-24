"""
RegimeX API v1 — Versioned Router
====================================
Aggregates all v1 endpoint routers and mounts them under /api/v1.

Adding new domain routers:
  1. Import the router from its endpoint module.
  2. Include it here with the appropriate prefix and tags.
  3. Do NOT add business logic in this module — routing only.

Example (for V05 Market Data):
    from app.api.v1.endpoints import market_data
    v1_router.include_router(market_data.router, prefix="/market-data")
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import auth, health, markets

v1_router = APIRouter(prefix="/api/v1")

# -------------------------------------------------------------------------
# Core / Infrastructure & Auth endpoints
# -------------------------------------------------------------------------
v1_router.include_router(health.router)
v1_router.include_router(markets.router)
v1_router.include_router(auth.router)


# -------------------------------------------------------------------------
# Domain endpoints — included in their respective volumes
# -------------------------------------------------------------------------
# v1_router.include_router(market_discovery.router)   # V05
# v1_router.include_router(market_data.router)         # V05
# v1_router.include_router(data_quality.router)        # V06
# v1_router.include_router(feature_engineering.router) # V07
# v1_router.include_router(regime_detection.router)    # V08
# v1_router.include_router(regime_intelligence.router) # V09
# v1_router.include_router(risk_analytics.router)      # V10
# v1_router.include_router(backtesting.router)         # V11
# v1_router.include_router(research_workspace.router)  # V12
# v1_router.include_router(ai_research.router)         # V21
# v1_router.include_router(identity_access.router)     # V15
# v1_router.include_router(administration.router)      # V16
