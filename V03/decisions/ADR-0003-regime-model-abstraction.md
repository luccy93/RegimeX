# ADR-0003: Regime Detection Model Abstraction

**Status:** Accepted  
**Date:** 2026-09-03  
**Volume:** V03 — System Architecture  
**Deciders:** RegimeX Core Architecture Team  

---

## 1. Context

Market regime detection is an evolving discipline in quantitative finance. Different mathematical methodologies offer distinct strengths and weaknesses across asset classes, sampling frequencies, and market environments:
- **Hidden Markov Models (HMM):** Capture unobserved latent states and transition dynamics under temporal Markovian assumptions.
- **Gaussian Mixture Models (GMM):** Segment feature distributions without temporal sequence constraints.
- **K-Means / Clustering:** Provide fast, deterministic geometric partitioning of volatility/return spaces.
- **Change Point Detection (e.g., PELT, BOCPD):** Identify structural breaks and regime boundary points.
- **Supervised & Deep Learning Models:** Future transformer-based or custom community neural architectures.

If downstream systems (regime intelligence, state transition analyzers, risk calculation engines, strategy backtesting allocators, and web dashboards) were coded against the idiosyncratic API of a specific model (e.g., `hmmlearn` vs `scikit-learn` vs custom PyTorch code), introducing a new algorithm would require rewriting consumers across the platform.

Furthermore, quantitative research demands that regime models expose not just arbitrary cluster integers, but rigorous probability distributions, model metadata, parameter configurations, and deterministic reproducibility seeds.

---

## 2. Decision

> **RegimeX mandates that all regime detection algorithms must implement a unified conceptual interface (`RegimeDetector`).**

1. **Common Lifecycle Contract:** Every regime model must support standardized lifecycle methods:
   - **Training / Fitting:** `fit(feature_matrix)` trains model parameters strictly using in-sample historical data.
   - **Inference / Prediction:** `predict(feature_matrix)` maps feature observations to discrete regime state labels ($0, 1, \dots, K-1$).
   - **Uncertainty / Probability Estimation:** `predict_proba(feature_matrix)` outputs continuous posterior probability vectors across all $K$ regimes where mathematically supported by the underlying algorithm (or calibrated one-hot approximations for deterministic algorithms).
2. **Standardized Model Metadata:** Every detector must expose self-describing metadata via `metadata()`, including human-readable algorithm name, mathematical family, assumptions, known failure modes, and hyperparameter schema.
3. **Model Versioning & Serialization:** Detectors must support versioned serialization (`save()` / `load()`) and record their exact parameter configuration (`get_params()`) to guarantee bit-for-bit historical reproducibility.
4. **Decoupled Consumer Interaction:** Downstream engines (risk analytics, transition matrix calculators, backtesting attribution) interact exclusively with the standard `RegimeDetector` protocol, remaining completely agnostic to whether the underlying model is an HMM, GMM, KMeans, or custom ensemble.
5. **Pluggable Registry:** Detectors register with a central `RegimeDetectorRegistry`, allowing users and researchers to select algorithms dynamically via configuration or API request parameters without code modifications.

*Note: Concrete implementation of specific algorithms begins in V08 (Hidden Markov Models) and V10 (GMM / Clustering).*

---

## 3. Alternatives Considered

| Alternative | Description | Why Not Chosen |
|-------------|-------------|----------------|
| **Standard scikit-learn BaseEstimator Directly** | Relying purely on scikit-learn's `fit/predict` conventions without a custom RegimeX contract. | scikit-learn's interface lacks standardized methods for regime-specific metadata, model parameter versioning, financial assumption disclosure, and regime probability normalization guarantees. |
| **Monolithic Detector Class with Internal Switch** | A single `RegimeEngine` class containing `if/else` branches for each algorithm. | Violates the Open/Closed Principle; prevents open-source contributors from adding custom models cleanly; leads to an unmaintainable god-class. |
| **Model Serving Microservice (e.g., MLflow, Triton)** | Running regime detection in an external ML model server. | Overkill for initial architecture; introduces heavy infrastructure dependencies (Docker, GPU clusters, RPC latency) that violate self-hosting principles. |

---

## 4. Consequences

### Positive
- **True Algorithmic Pluggability:** Researchers and community developers can implement custom detection models simply by conforming to the `RegimeDetector` contract.
- **Fair Benchmarking:** Multiple algorithms can be executed against identical feature matrices and evaluated side-by-side using the same risk engines and backtest simulators.
- **Enforced Financial Rigor:** The interface mandates probabilistic outputs and assumption disclosures, directly aligning with RegimeX's core principle of explicit uncertainty communication.
- **Deterministic Testing:** Automated compliance suites (`tests/compliance/test_regime_detector_compliance.py`) can test any model implementation for look-ahead bias, output dimensions, and NaN resilience.

### Negative / Trade-offs
- **Lowest Common Denominator Constraint:** Algorithms with highly specialized capabilities (e.g., streaming Bayesian updates) must conform to the batch matrix interface, potentially requiring custom auxiliary methods for advanced behaviors.

---

## 5. Requirements Addressed

- **V01 Project Scope:** Multiple interchangeable regime detection models (HMM, GMM, KMeans, Changepoint).
- **V02 Functional Requirements:**
  - `FR-022`: Standard `RegimeDetector` interface requirement.
  - `FR-023`–`FR-031`: Interchangeable regime detection models and validation.
- **V02 Non-Functional Requirements:**
  - `NFR-030`: Feature and model plugin scalability.
  - `NFR-032`: Research reproducibility.
  - `NFR-078`: Plugin and detector interface stability.
  - `NFR-101`: Uncertainty communication (probability distributions).
