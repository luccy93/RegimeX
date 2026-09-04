# RegimeX

### Open-Source Market Intelligence Platform

RegimeX is an open-source platform that gives quantitative researchers, market analysts, and developers the infrastructure to understand market regimes — what they are, how they evolve, what risks they carry, and how strategies behave across them.

> **Status:** Pre-Alpha · V04 Engineering Foundation · Application skeleton established

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

> Application capabilities listed above are not yet implemented. RegimeX is establishing its engineering foundation in V04. See [`V01/PROJECT_STATUS.md`](V01/PROJECT_STATUS.md) for implementation status.

---

## What RegimeX Is Not

RegimeX explicitly does **not** and will **not**:

- ❌ Provide personalized financial or investment advice
- ❌ Predict stock prices or guarantee trading outcomes
- ❌ Execute trades or interface with brokers
- ❌ Hide its assumptions, methodologies, or uncertainty
- ❌ Lock users into proprietary data vendors or cloud platforms

---

## Quick Start (V04 Foundation)

```bash
# 1. Clone the repository
git clone https://github.com/luccy93/RegimeX.git
cd RegimeX

# 2. Start infrastructure services
docker compose -f infra/docker-compose.yml up -d db redis

# 3. Run the backend
cd apps/api
python -m venv .venv
.venv\Scripts\activate           # Windows
# source .venv/bin/activate      # macOS/Linux
pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# 4. Run tests (new terminal)
cd apps/api
pytest tests/ -v

# 5. Run the frontend (new terminal)
cd apps/web
npm install
cp .env.example .env.local
npm run dev
```

- API: http://localhost:8000
- API Docs: http://localhost:8000/api/docs
- Health: http://localhost:8000/api/v1/health/live
- Web: http://localhost:3000

---

## Project Status

| Volume | Title | Status |
|--------|-------|--------|
| **V01** | **Product Foundation** | ✅ Complete |
| **V02** | **Enterprise Requirements** | ✅ Complete |
| **V03** | **System Architecture** | ✅ Complete |
| **V04** | **Monorepo Engineering Foundation** | ⚙️ In Progress |
| V05–V12 | Data & Intelligence Pipeline | 🔜 Planned |
| V13–V15 | Quantitative Analytics | 🔜 Planned |
| V16–V21 | Platform & AI Research | 🔜 Planned |
| V22–V26 | Production | 🔜 Planned |
| V27–V30 | Open Source & 1.0 Release | 🔜 Planned |

See the full 30-volume roadmap: [`V01/PRODUCT_ROADMAP.md`](V01/PRODUCT_ROADMAP.md)

---

## Repository Structure

```text
RegimeX/
├── apps/
│   ├── api/                    ← FastAPI backend (Python 3.12)
│   └── web/                    ← Next.js frontend (TypeScript)
├── packages/
│   ├── contracts/              ← Shared API type contracts
│   └── config/                 ← Shared configuration schemas
├── tests/
│   ├── integration/            ← Multi-service integration tests
│   └── e2e/                    ← End-to-end browser tests
├── docs/
│   └── V04/                    ← V04 engineering guide
├── scripts/                    ← Operational scripts
├── infra/
│   ├── docker-compose.yml      ← Local development topology
│   └── docker/                 ← Dockerfiles
├── V01/                        ← Product Foundation documentation
├── V02/                        ← Enterprise Requirements documentation
├── V03/                        ← System Architecture documentation
├── .gitignore
├── .editorconfig
└── README.md
```

For the full engineering guide, see [`docs/V04/README.md`](docs/V04/README.md).

---

## Architecture Direction

RegimeX is designed as a **Modular Monolith with Asynchronous Workers** — a decision formalized in V03 ([ADR-0001](V03/decisions/ADR-0001-architecture-style.md)).

Key architectural principles:
- **Provider abstraction** — market data providers are swappable without changing business logic
- **Model abstraction** — regime detection algorithms conform to a standard interface
- **No look-ahead bias** — quantitative computation is strictly point-in-time
- **Reproducibility** — every analysis is reproducible from its data version and configuration
- **Open-source first** — no proprietary dependencies required for self-hosting

Full architecture: [`V03/ARCHITECTURE.md`](V03/ARCHITECTURE.md)  
Module boundaries: [`V03/MODULE_BOUNDARIES.md`](V03/MODULE_BOUNDARIES.md)

---

## Documentation

| Document | Purpose |
|----------|---------|
| [`docs/V04/README.md`](docs/V04/README.md) | V04 engineering guide — how the repo implements V03 |
| [`docs/V04/ARCHITECTURE_GUARDRAILS.md`](docs/V04/ARCHITECTURE_GUARDRAILS.md) | Rules preventing architectural drift |
| [`V03/ARCHITECTURE.md`](V03/ARCHITECTURE.md) | System architecture blueprint |
| [`V03/MODULE_BOUNDARIES.md`](V03/MODULE_BOUNDARIES.md) | Module boundary specifications |
| [`V02/SRS.md`](V02/SRS.md) | Enterprise software requirements |
| [`V01/PRODUCT_ROADMAP.md`](V01/PRODUCT_ROADMAP.md) | Full 30-volume roadmap |
| [`V01/CONTRIBUTING.md`](V01/CONTRIBUTING.md) | How to contribute |
| [`V01/PROJECT_STATUS.md`](V01/PROJECT_STATUS.md) | Current implementation status |

---

## Contributing

Contributions are welcome. Please read [`V01/CONTRIBUTING.md`](V01/CONTRIBUTING.md) before opening issues or pull requests.

From V04 onward, code contributions are open. Start with:
1. Read the [V04 Engineering Guide](docs/V04/README.md)
2. Understand the [Architectural Guardrails](docs/V04/ARCHITECTURE_GUARDRAILS.md)
3. Pick a module from the [Module Timeline](docs/V04/README.md#module-implementation-timeline)
4. Follow the module anatomy pattern

---

## License

License will be declared in a forthcoming ADR (OQ-010). RegimeX intends to be fully open-source.

---

## Disclaimer

RegimeX is an open-source research and analytics platform. It does **not** provide financial advice, personalized investment recommendations, or any guarantee of financial returns. All platform outputs are for informational and research purposes only. Users are solely responsible for any decisions made based on platform outputs.
