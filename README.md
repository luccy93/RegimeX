# RegimeX

### Open-Source Market Intelligence Platform

RegimeX is an open-source platform that gives quantitative researchers, market analysts, and developers the infrastructure to understand market regimes — what they are, how they evolve, what risks they carry, and how strategies behave across them.

> **Status:** Pre-Alpha · V01 Product Foundation · No application code yet

---

## What RegimeX Is

RegimeX is **market intelligence and quantitative research infrastructure**.

The platform is designed to answer questions practitioners ask constantly:

- **What market regime exists right now?**
- **How did we get here — and how long have we been here?**
- **What risks does this regime historically carry?**
- **How have quantitative strategies performed across different regimes?**

RegimeX provides the data, feature engineering, regime detection, risk analytics, and backtesting infrastructure to answer these questions rigorously — with auditable methodology, explicit uncertainty, and zero tolerance for look-ahead bias.

---

## Product Vision

RegimeX will become a comprehensive open-source platform for:

| Capability | Description |
|-----------|-------------|
| **Market Data** | Provider-independent ingestion and normalization of historical market data |
| **Feature Engineering** | Reproducible, point-in-time quantitative feature computation |
| **Regime Detection** | Multiple configurable algorithms (HMM, GMM, ensemble, changepoint) |
| **Regime Intelligence** | Transition analysis, persistence metrics, regime-conditional statistics |
| **Risk Analytics** | Regime-aware VaR, CVaR, drawdown, correlation dynamics |
| **Backtesting** | Event-driven strategy simulation with realistic transaction costs |
| **Research Workspace** | Reproducible, versioned quantitative research environment |
| **AI Research Assistant** | Grounded AI assistant that cites platform data and acknowledges uncertainty |
| **API Platform** | REST API for programmatic access to all platform capabilities |
| **Web Platform** | Browser-based analytics for public users and researchers |

> None of the above capabilities are implemented yet. RegimeX is in its product foundation phase. See [`V01/PROJECT_STATUS.md`](V01/PROJECT_STATUS.md) for the full implementation status.

---

## What RegimeX Is Not

RegimeX explicitly does **not** and will **not**:

- ❌ Provide personalized financial or investment advice
- ❌ Predict stock prices or guarantee trading outcomes
- ❌ Execute trades or interface with brokers
- ❌ Hide its assumptions, methodologies, or uncertainty
- ❌ Lock users into proprietary data vendors or cloud platforms

---

## Target Users

| User | What RegimeX Provides |
|------|----------------------|
| **Public users** | Regime dashboards, market state overviews (via web platform) |
| **Market researchers** | Historical regime data, exportable analytics |
| **Quantitative researchers** | Feature library, regime detection, backtesting, research workspace |
| **Developers** | REST API, Python SDK, extension interfaces |
| **Open-source contributors** | Plugin system, algorithm contribution, provider adapters |
| **Platform administrators** | Self-hosting support, full operational control |

---

## Architecture Direction

RegimeX is being designed as a **modular, provider-independent, self-hostable** platform.

Key architectural principles:
- **Provider abstraction** — market data providers are swappable without changing business logic
- **Model abstraction** — regime detection algorithms conform to a standard interface
- **No look-ahead bias** — quantitative computation is strictly point-in-time
- **Reproducibility** — every analysis is reproducible from its data version and configuration
- **Open-source first** — no proprietary dependencies required for self-hosting

The full system architecture will be defined in **V03 — System Architecture**.

---

## Open-Source Positioning

RegimeX is built for the open-source community:

- **Self-hostable** — run the full platform without proprietary cloud services
- **Extensible** — contribute new algorithms, data providers, and features through a standard plugin system
- **Transparent** — every model, feature, and risk metric is documented with its assumptions and limitations
- **Community-governed** — architectural decisions are made openly and recorded as ADRs

---

## Project Status

RegimeX is in **V01 — Product Foundation**. This is a pre-alpha, documentation-only phase.

| Volume | Title | Status |
|--------|-------|--------|
| **V01** | **Product Foundation** | ✅ In Progress |
| V02 | Enterprise Requirements | 🔜 Planned |
| V03 | System Architecture | 🔜 Planned |
| V04 | Monorepo Engineering Foundation | 🔜 Planned |
| V05–V12 | Data & Intelligence | 🔜 Planned |
| V13–V15 | Quantitative Analytics | 🔜 Planned |
| V16–V21 | Platform | 🔜 Planned |
| V22–V26 | Production | 🔜 Planned |
| V27–V30 | Open Source & 1.0 Release | 🔜 Planned |

See the full 30-volume roadmap: [`V01/PRODUCT_ROADMAP.md`](V01/PRODUCT_ROADMAP.md)

---

## Repository Structure

```text
RegimeX/
├── README.md                       ← You are here
└── V01/                            ← Product Foundation
    ├── README.md                   ← Volume introduction and roadmap
    ├── PRODUCT_FOUNDATION.md       ← Vision, positioning, users, product areas
    ├── PROJECT_SCOPE.md            ← In-scope and out-of-scope boundaries
    ├── PRINCIPLES.md               ← Product, engineering, quantitative principles
    ├── PRODUCT_ROADMAP.md          ← 30-volume development roadmap
    ├── DEVELOPMENT_GUIDE.md        ← Git workflow, commits, volume structure
    ├── CONTRIBUTING.md             ← Contributor guide
    ├── PROJECT_STATUS.md           ← Current implementation status
    └── decisions/
        └── README.md              ← Architecture Decision Record (ADR) index
```

---

## Documentation

| Document | Purpose |
|----------|---------|
| [`V01/PRODUCT_FOUNDATION.md`](V01/PRODUCT_FOUNDATION.md) | Product vision, positioning, target users |
| [`V01/PROJECT_SCOPE.md`](V01/PROJECT_SCOPE.md) | Explicit scope boundaries |
| [`V01/PRINCIPLES.md`](V01/PRINCIPLES.md) | Engineering and product principles |
| [`V01/PRODUCT_ROADMAP.md`](V01/PRODUCT_ROADMAP.md) | Full 30-volume roadmap |
| [`V01/DEVELOPMENT_GUIDE.md`](V01/DEVELOPMENT_GUIDE.md) | Development workflow and conventions |
| [`V01/CONTRIBUTING.md`](V01/CONTRIBUTING.md) | How to contribute |
| [`V01/PROJECT_STATUS.md`](V01/PROJECT_STATUS.md) | Current implementation status |
| [`V01/decisions/README.md`](V01/decisions/README.md) | Architecture Decision Records |

---

## Contributing

Contributions are welcome. Please read [`V01/CONTRIBUTING.md`](V01/CONTRIBUTING.md) before opening issues or pull requests.

At this stage (V01), the most valuable contributions are:
- Reviewing and improving foundation documentation
- Identifying gaps or contradictions in scope and principles
- Proposing ADRs for architectural decisions

Code contribution workflows will be fully operational from V04 onward.

---

## License

License will be declared in V02 — Enterprise Requirements. RegimeX intends to be fully open-source.

---

## Disclaimer

RegimeX is an open-source research and analytics platform. It does **not** provide financial advice, personalized investment recommendations, or any guarantee of financial returns. All platform outputs are for informational and research purposes only. Users are solely responsible for any decisions made based on platform outputs.
