# Conceptual Interface Specifications

**RegimeX — Open-Source Market Intelligence Platform**  
**Volume:** V03 — System Architecture  
**Status:** Approved Architecture Blueprint  

---

## 1. Overview

This document specifies the conceptual interface contracts between major RegimeX modules. These abstract contracts define the extension points of the platform, enabling modularity, testability, community extensibility, and vendor independence.

> ⚠️ **Design Specification Notice:** These interfaces represent **conceptual contracts and pseudocode specifications** governing architectural boundaries. Full concrete Python implementations (using `abc.ABC`, `typing.Protocol`, and Pydantic v2 schemas) begin in implementation volumes (V04–V16).

---

## 2. Core Conceptual Contracts

### 2.1 `MarketDataProvider` Contract

**Module:** `regimex.data.providers.base`  
**Purpose:** Abstracts over external financial market data sources, guaranteeing vendor independence.

```python
from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Iterator, Dict, Any, List
from regimex.core.types import Symbol, Exchange, AssetClass, Timeframe
from regimex.data.schema import OHLCVRecord, ProviderMetadata, ProviderFreshness

class MarketDataProvider(ABC):
    """
    Conceptual interface for external market data providers.
    All external data sources (Yahoo Finance, Alpha Vantage, Polygon, etc.)
    must implement this contract.
    """

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Unique identifier for this provider adapter (e.g., 'yahoo_finance')."""
        ...

    @property
    @abstractmethod
    def provider_version(self) -> str:
        """Semantic version of the adapter implementation."""
        ...

    @abstractmethod
    def supports(self, symbol: Symbol, exchange: Exchange) -> bool:
        """Determines if this provider supports the requested instrument/exchange."""
        ...

    @abstractmethod
    def get_supported_symbols(self, asset_class: AssetClass | None = None) -> List[Symbol]:
        """Returns the catalogue of symbols discoverable from this provider."""
        ...

    @abstractmethod
    def fetch_ohlcv(
        self,
        symbol: Symbol,
        exchange: Exchange,
        start: date,
        end: date,
        timeframe: Timeframe = Timeframe.DAILY,
        adjustment_type: str = "SPLIT_ADJUSTED",
    ) -> Iterator[OHLCVRecord]:
        """
        Fetches historical OHLCV records in ascending chronological order.
        
        Contract Guarantees:
        - Must yield records sorted chronologically (t[i] < t[i+1]).
        - Must never yield records outside [start, end].
        - Must translate vendor network/HTTP errors into RegimeX DataError hierarchy.
        - Must attach source provider_id and fetch timestamp metadata to each record.
        """
        ...

    @abstractmethod
    def get_freshness_metadata(self, symbol: Symbol) -> ProviderFreshness:
        """
        Returns data freshness status, including last available trading date
        and upstream feed update latency.
        """
        ...
```

---

### 2.2 `FeatureProvider` & Feature Pipeline Contract

**Module:** `regimex.features.base`  
**Purpose:** Defines quantitative mathematical feature transformers with strict point-in-time enforcement.

```python
from abc import ABC, abstractmethod
from datetime import datetime
import pandas as pd
from regimex.features.schema import FeatureValue, FeatureMetadata

class FeatureProvider(ABC):
    """
    Conceptual interface for a quantitative feature calculation.
    """

    @property
    @abstractmethod
    def feature_id(self) -> str:
        """Unique versioned identifier (e.g., 'realized_vol_21d_v1')."""
        ...

    @property
    @abstractmethod
    def feature_version(self) -> str:
        """Semantic version of the calculation algorithm."""
        ...

    @property
    @abstractmethod
    def min_bars_required(self) -> int:
        """Minimum historical observations needed to produce a valid calculation."""
        ...

    @abstractmethod
    def compute(
        self,
        historical_data: pd.DataFrame,
        as_of_timestamp: datetime,
    ) -> FeatureValue:
        """
        Computes the feature value at a specific point in time.

        Strict Architectural Guarantees:
        - Point-in-Time Correctness: historical_data MUST be filtered such that
          all records have timestamp <= as_of_timestamp.
        - Look-ahead bias violation is classified as a critical defect.
        - Returns is_valid=False when historical observations < min_bars_required.
        - Deterministic: Same input matrix -> identical feature value.
        """
        ...

    @abstractmethod
    def metadata(self) -> FeatureMetadata:
        """Returns feature documentation, mathematical formula, and parameters."""
        ...
```

---

### 2.3 `RegimeDetector` Contract

**Module:** `regimex.regime.detectors.base`  
**Purpose:** Unified contract for unsupervised, statistical, and machine learning market regime detection.

```python
from abc import ABC, abstractmethod
import pandas as pd
import numpy as np
from typing import Dict, Any
from regimex.regime.schema import DetectorMetadata, RegimeInferenceResult

class RegimeDetector(ABC):
    """
    Conceptual interface for regime detection algorithms.
    Supported model families: HMM, GMM, KMeans, Changepoint, Community Models.
    """

    @property
    @abstractmethod
    def algorithm_id(self) -> str:
        """Unique versioned algorithm identifier (e.g., 'hmm_gaussian_v1')."""
        ...

    @property
    @abstractmethod
    def algorithm_version(self) -> str:
        """Semantic version of the detector model implementation."""
        ...

    @abstractmethod
    def fit(self, feature_matrix: pd.DataFrame) -> "RegimeDetector":
        """
        Fits model parameters strictly using in-sample feature data.
        
        Args:
            feature_matrix: DataFrame indexed by timestamp, columns are standardized features.
        Returns:
            self (trained model instance)
        """
        ...

    @abstractmethod
    def predict(self, feature_matrix: pd.DataFrame) -> np.ndarray:
        """
        Predicts discrete integer regime states [0, 1, ..., K-1] for each row.
        Length of output array must match len(feature_matrix) exactly.
        """
        ...

    @abstractmethod
    def predict_proba(self, feature_matrix: pd.DataFrame) -> np.ndarray:
        """
        Predicts continuous posterior probability distributions across all K states.
        
        Contract Guarantees:
        - Output shape: (n_samples, n_regimes).
        - Every row must sum to 1.0 within floating-point tolerance (1e-6).
        - Non-probabilistic algorithms must provide calibrated confidence vectors.
        """
        ...

    @abstractmethod
    def get_params(self) -> Dict[str, Any]:
        """Returns the complete hyperparameter configuration for exact reproducibility."""
        ...

    @abstractmethod
    def metadata(self) -> DetectorMetadata:
        """Exposes algorithm documentation, assumptions, and known limitation disclosures."""
        ...
```

---

### 2.4 `RiskEngine` Contract

**Module:** `regimex.risk.base`  
**Purpose:** Computes portfolio and asset risk metrics, both unconditional and conditioned on regime states.

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import pandas as pd
from regimex.risk.schema import RiskMetricSet, RiskConfiguration

class RiskEngine(ABC):
    """
    Conceptual contract for unconditional and regime-conditional risk analytics.
    """

    @abstractmethod
    def compute_asset_risk(
        self,
        returns: pd.Series,
        config: RiskConfiguration,
        regime_timeline: Optional[pd.Series] = None,
    ) -> RiskMetricSet:
        """
        Computes standard and regime-conditional risk metrics.

        Metrics Produced:
        - Value at Risk (VaR) at alpha (95%, 99%)
        - Conditional Value at Risk (CVaR / Expected Shortfall)
        - Maximum Drawdown, Drawdown Duration, and Recovery Factor
        - Regime-conditional volatility and return distributions

        Contract Guarantees:
        - Explicitly discloses confidence levels and historical sample windows.
        - Provenance record captures input returns fingerprint and regime_run_id.
        - Zero guaranteed financial return claims (adheres to NFR-099).
        """
        ...
```

---

### 2.5 `BacktestEngine` & Strategy Contract

**Module:** `regimex.backtest.base`  
**Purpose:** Event-driven historical simulation with realistic cost attribution and regime performance breakdown.

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import pandas as pd
from regimex.backtest.schema import (
    BacktestResult,
    BacktestConfiguration,
    PortfolioState,
    Signal,
    Fill
)

class CostModel(ABC):
    """Abstract transaction cost and slippage calculator."""
    @abstractmethod
    def calculate_cost(self, fill: Fill) -> float: ...

class Strategy(ABC):
    """User-defined quantitative strategy callback interface."""
    @abstractmethod
    def on_bar(
        self,
        current_bar: pd.Series,
        portfolio: PortfolioState,
        regime_state: Optional[int] = None
    ) -> List[Signal]:
        """
        Executed once per bar chronologically.
        Current bar contains data ONLY up to the current timestamp.
        """
        ...

class BacktestEngine(ABC):
    """Event-driven chronological backtesting simulation engine."""

    @abstractmethod
    def run(
        self,
        strategy: Strategy,
        universe: List[str],
        data_matrix: pd.DataFrame,
        config: BacktestConfiguration,
        cost_model: CostModel,
        regime_timeline: Optional[pd.Series] = None,
    ) -> BacktestResult:
        """
        Simulates strategy execution over historical bars.

        Contract Guarantees:
        - Chronological order enforced: bar[t] processed strictly before bar[t+1].
        - Transaction costs and execution slippage subtracted from portfolio cash.
        - Attribution breakdown by detected regime states (Sharpe/Drawdown per regime).
        - Provenance captured: Strategy parameters, cost config, dataset fingerprint.
        """
        ...
```

---

### 2.6 `AIProviderAdapter` Contract

**Module:** `regimex.ai.base`  
**Purpose:** Provider-agnostic interface for external foundation LLMs with strict context grounding and safety filters.

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from regimex.ai.schema import GroundingPayload, AIResponse, SafetyValidationResult

class AIProviderAdapter(ABC):
    """
    Conceptual interface for grounded AI foundation model interactions.
    """

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Provider name (e.g., 'openai', 'anthropic', 'local_llama')."""
        ...

    @abstractmethod
    def generate_grounded_response(
        self,
        user_query: str,
        grounding_context: GroundingPayload,
        system_policy_template: str,
    ) -> AIResponse:
        """
        Dispatches a grounded analytical query to the AI provider.

        Contract Guarantees:
        - Model receives verified structured platform data (no raw database access).
        - System prompt strictly prohibits personalized financial advice (NFR-100).
        - Sanitizes input: never forwards database credentials or secret keys.
        - Response metadata includes model version, token usage, and provenance links.
        - Output passes through response validation gate before presentation.
        """
        ...

    @abstractmethod
    def validate_safety(self, raw_response: str) -> SafetyValidationResult:
        """
        Validates output against anti-hallucination and anti-advisory policy rules.
        """
        ...
```

---

## 3. Compliance Verification

All concrete implementations of these conceptual contracts will be validated by dedicated compliance test suites:
- `tests/compliance/test_provider_compliance.py`
- `tests/compliance/test_feature_compliance.py`
- `tests/compliance/test_regime_detector_compliance.py`
- `tests/compliance/test_cost_model_compliance.py`
- `tests/compliance/test_strategy_compliance.py`
- `tests/compliance/test_ai_provider_compliance.py`
