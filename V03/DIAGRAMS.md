# RegimeX Architecture Diagrams

**RegimeX — Open-Source Market Intelligence Platform**  
**Volume:** V03 — System Architecture  
**Status:** Approved Architecture Blueprint  

---

## 1. Overview

This document provides formal architectural diagrams for RegimeX using standard Mermaid and structured ASCII representations. These diagrams illustrate system context, runtime container architecture, quantitative data pipeline validation gates, grounded AI workflows, and multi-tier security boundaries.

---

## 2. System Context Diagram

The System Context diagram illustrates RegimeX's external actors, consumer boundaries, core platform capabilities, and third-party foundation integrations.

```mermaid
flowchart TD
    subgraph Users["Platform Consumers & Actors"]
        PublicUser["Public User / Analyst\n(Unauthenticated Exploration)"]
        Researcher["Quantitative Researcher\n(Authenticated Workspaces)"]
        Developer["Algorithmic Developer\n(API & Custom Plugins)"]
        Administrator["Platform Administrator\n(System Operations & Audit)"]
    end

    subgraph Platform["RegimeX Platform"]
        WebApp["Web Presentation Tier\n(Next.js Dashboard & Visualization)"]
        APIGateway["API Gateway & Application Tier\n(FastAPI, Auth, Rate Limiting)"]
        
        subgraph CorePlatform["Core Intelligence & Processing"]
            DomainEngine["Domain Engine\n(Discovery, Features, Regime, Risk)"]
            BacktestEngine["Event-Driven Backtester\n(Cost Models & Attribution)"]
            AIEngine["Grounded AI Engine\n(Context Retrieval & Citations)"]
            WorkerCluster["Asynchronous Worker Cluster\n(Celery Compute Nodes)"]
        end
        
        subgraph StorageLayer["Persistence & Caching"]
            Database[("PostgreSQL + TimescaleDB\nHypertables & Relational ACID")]
            CacheQueue[("Redis\nCache & Message Broker")]
        end
    end

    subgraph External["External Services & Upstream Providers"]
        MarketDataVendors["External Market Data Providers\n(Yahoo Finance, Alpha Vantage, Polygon)"]
        AIProviders["External AI / LLM Providers\n(OpenAI, Anthropic, Self-Hosted)"]
    end

    PublicUser -->|HTTPS Browse| WebApp
    Researcher -->|HTTPS Auth / Workspaces| WebApp
    Developer -->|REST API / WebSockets| APIGateway
    Administrator -->|HTTPS Admin Operations| WebApp

    WebApp -->|HTTPS API Requests| APIGateway
    APIGateway -->|In-Process Execution| DomainEngine
    APIGateway -->|In-Process Execution| BacktestEngine
    APIGateway -->|In-Process Execution| AIEngine
    APIGateway -->|Enqueue Heavy Jobs| CacheQueue
    
    CacheQueue -->|Consume Tasks| WorkerCluster
    WorkerCluster -->|Run Pipelines| DomainEngine
    WorkerCluster -->|Run Simulations| BacktestEngine
    
    DomainEngine -->|Read / Write| Database
    BacktestEngine -->|Read / Write| Database
    AIEngine -->|Read Only Grounding| Database
    APIGateway -->|Read Cached State| CacheQueue

    DomainEngine -->|Outbound Adapter Calls| MarketDataVendors
    AIEngine -->|Outbound Sanitized Prompts| AIProviders
```

---

## 3. Container & Runtime Architecture

The Container Architecture details the logical processes, network segregation, and execution boundaries between synchronous user paths and asynchronous compute workers.

```mermaid
flowchart TD
    Client["Client Browser / SDK Client"]

    subgraph Edge["Edge / Reverse Proxy Tier"]
        Proxy["Caddy / Reverse Proxy\n(TLS Termination, Compression, Static Assets)\nPorts: 80, 443"]
    end

    subgraph AppTier["Application Tier (Stateless)"]
        API["FastAPI API Server\n(Routing, Pydantic Validation, Auth, Rate Limiting)\nPort: 8000"]
        Web["Next.js Web Server\n(SSR, Interactive Charts, React UI)\nPort: 3000"]
    end

    subgraph ComputeTier["Asynchronous Compute Tier (Workers)"]
        Worker1["Celery Worker Node 1\n(Data Ingestion & Feature Generation)"]
        Worker2["Celery Worker Node 2\n(Regime Model Training & Backtesting)"]
        Scheduler["Celery Beat\n(Periodic Ingestion Scheduler)"]
    end

    subgraph DataTier["Data & Persistence Tier (Stateful)"]
        RedisNode[("Redis 7+\n(Message Broker & Fast Key-Value Cache)\nPort: 6379")]
        PostgresNode[("PostgreSQL 15+ & TimescaleDB\n(Relational ACID & Time-Series Hypertables)\nPort: 5432")]
    end

    subgraph ExternalTier["External Egress Tier"]
        DataProvider["Market Data Vendor APIs"]
        LLMProvider["LLM Foundation APIs"]
    end

    Client -->|HTTPS| Proxy
    Proxy -->|Proxy UI Traffic| Web
    Proxy -->|Proxy API Traffic| API

    Web -->|Internal HTTP| API

    API -->|Read/Write Metadata| PostgresNode
    API -->|Read/Write Cache & Session| RedisNode
    API -->|Dispatch Async Tasks| RedisNode

    RedisNode -->|Task Queue Dispatch| Worker1
    RedisNode -->|Task Queue Dispatch| Worker2
    Scheduler -->|Enqueue Cron Tasks| RedisNode

    Worker1 -->|Batch OHLCV & Features| PostgresNode
    Worker2 -->|Model State & Backtest Runs| PostgresNode

    Worker1 -->|Outbound Ingestion| DataProvider
    API -->|Outbound Grounded Prompts| LLMProvider
```

---

## 4. Market Intelligence Pipeline (Validation Gates)

The Market Intelligence Pipeline enforces sequential data integrity checks and strict point-in-time constraints from raw external ingestion through quantitative modeling to risk analytics.

```mermaid
flowchart TD
    UpstreamData["Upstream Market Data Provider\n(Vendor Specific API)"]

    subgraph IngestionBoundary["1. Ingestion & Normalization"]
        Adapter["Provider Adapter\n(Maps vendor schema to internal raw struct)"]
        
        Gate1{"Validation Gate 1\nSyntax & Sanity"}
        Gate1Fail["Quarantine / Log Error\n(Drop malformed record)"]
        
        Normalizer["Normalizer & Typer\n(UTC Timestamp, Decimal conversion, Splits/Divs)"]
        
        Gate2{"Validation Gate 2\nOHLCV Consistency Constraints"}
        Gate2Fail["Quarantine to data_quality_events\n(Flag price/calendar anomaly)"]
        
        CanonicalDB[("Canonical Market Data Store\n(Immutable, SHA-256 Fingerprinted)")]
    end

    subgraph FeatureBoundary["2. Feature Engineering"]
        PointInTimeSlice["Point-in-Time Data Slice\n(Filter records where t <= T)"]
        FeatureEngine["Feature Pipeline\n(Returns, Realized Vol, Momentum, ATR)"]
        
        Gate3{"Validation Gate 3\nLook-Ahead & Numeric Sanity"}
        Gate3Fail["Critical System Abort\n(Throw LookAheadBiasError / Set is_valid=False)"]
        
        FeatureMatrix["Validated Feature Matrix\n(Standardized, No Future Leaks)"]
    end

    subgraph ModelBoundary["3. Regime Intelligence"]
        ModelRegistry["Regime Detector Registry\n(HMM, GMM, KMeans, Changepoint)"]
        ModelFit["Model Fitting / Inference\n(fit() on in-sample, predict() on slice)"]
        
        Gate4{"Validation Gate 4\nProbability Normalization"}
        Gate4Fail["Model Convergence Error\n(Sum of probabilities != 1.0)"]
        
        RegimeTimeline["Regime Classification Timeline\n(Discrete Labels + Soft Probabilities)"]
        
        Transitions["Regime Intelligence Engine\n(Transition Matrix & State Persistence)"]
    end

    subgraph DownstreamBoundary["4. Risk & Backtesting Delivery"]
        RiskEngine["Risk Engine\n(Regime-Conditional VaR & CVaR)"]
        BacktestEngine["Backtest Engine\n(Event-Driven Order Simulation & Cost Attribution)"]
        ResearchArtifacts["Research Run Artifact\n(Full Provenance, Seeds, Reproducibility Bundle)"]
    end

    UpstreamData --> Adapter
    Adapter --> Gate1
    Gate1 -- Invalid --> Gate1Fail
    Gate1 -- Valid --> Normalizer
    Normalizer --> Gate2
    Gate2 -- Violated --> Gate2Fail
    Gate2 -- Passed --> CanonicalDB

    CanonicalDB --> PointInTimeSlice
    PointInTimeSlice --> FeatureEngine
    FeatureEngine --> Gate3
    Gate3 -- Leak/NaN --> Gate3Fail
    Gate3 -- Clean --> FeatureMatrix

    FeatureMatrix --> ModelFit
    ModelRegistry -.->|Inject Model Contract| ModelFit
    ModelFit --> Gate4
    Gate4 -- Invalid --> Gate4Fail
    Gate4 -- Normalized --> RegimeTimeline

    RegimeTimeline --> Transitions
    RegimeTimeline --> RiskEngine
    RegimeTimeline --> BacktestEngine
    Transitions --> ResearchArtifacts
    RiskEngine --> ResearchArtifacts
    BacktestEngine --> ResearchArtifacts
```

---

## 5. Grounded AI Research Pipeline

The Grounded AI Architecture ensures that external foundation models have **zero direct database access** and are strictly constrained by verified analytical facts and anti-financial-advice guardrails.

```mermaid
flowchart TD
    UserQuery["User Research Question\n(e.g., 'What was the regime stability during the 2020 crash?')"]

    subgraph CorePlatformBoundary["RegimeX Controlled Application Boundary"]
        ContextBuilder["Research Context Builder\n(Deconstructs query into analytical parameters)"]
        
        subgraph InternalDataQuery["Authorized Data Retrieval (Internal Service Layer)"]
            Retriever["RegimeX Domain Retriever\n(Queries verified internal repositories)"]
            RegimeData[("Regime Timelines & Transition Probabilities")]
            RiskData[("Computed Risk Metrics & Drawdowns")]
            AuditData[("Run Metadata & Provenance Fingerprints")]
        end

        GroundingPayload["Structured Grounding Context\n(Verified facts, run_ids, dates, confidence scores)"]
        
        PromptAssembler["System Prompt & Safety Template\n(Mandates citations, strict prohibition of investment advice)"]
        
        ProviderAdapter["AI Provider Adapter\n(Sanitizes payload, strips internal credentials)"]
    end

    subgraph ExternalLLMBoundary["External AI Foundation Provider"]
        LLM["Foundation Model (OpenAI / Anthropic / Local)\n[NO DIRECT ACCESS TO REGIMEX DATABASE]"]
    end

    subgraph ValidationBoundary["Response Safety & Provenance Gate"]
        OutputValidator{"Output Safety & Fact Validator"}
        AdviceBlocked["Reject / Redact Response\n(Prohibit financial advice or ungrounded claims)"]
        ApprovedResponse["Grounded Response with Citations\n(Cites run_id, probabilities, and financial disclaimers)"]
    end

    UserQuery --> ContextBuilder
    ContextBuilder --> Retriever
    
    Retriever <--> RegimeData
    Retriever <--> RiskData
    Retriever <--> AuditData
    
    Retriever --> GroundingPayload
    GroundingPayload --> PromptAssembler
    PromptAssembler --> ProviderAdapter
    
    ProviderAdapter -->|HTTPS Outbound Call Only| LLM
    LLM -->|Raw Generated Text| OutputValidator

    OutputValidator -- Advisory / Fabricated Language --> AdviceBlocked
    OutputValidator -- Verified & Safe --> ApprovedResponse
    
    ApprovedResponse --> ClientUser["User Presentation / Web Interface"]
```

---

## 6. Security & Trust Boundaries

The Security Architecture diagram maps the concentric trust perimeters, authentication checkpoints, and data access policies from the public perimeter to isolated internal storage.

```mermaid
flowchart TD
    subgraph Zone0["Untrusted Zone: Public Internet"]
        ExternalTraffic["Inbound HTTPS Traffic / Web Clients / API Consumers"]
    end

    subgraph Perimeter["Perimeter Security Barrier"]
        TLS["TLS 1.2+ Termination (Caddy Proxy)"]
        RateLimiter["Sliding-Window Rate Limiter (Redis IP Buckets)"]
    end

    subgraph Zone1["DMZ / Gateway Tier: Publicly Accessible Services"]
        APIGateway["FastAPI Application"]
        AuthModule{"Authentication Boundary\n(API Key Hash / JWT Validation)"}
        PublicEndpoints["Public Endpoints\n(Health, Docs, Catalog Discovery)"]
    end

    subgraph Zone2["Protected Application Tier: Authenticated Context"]
        RBAC{"RBAC Authorization Gate\n(Researcher vs Admin)"}
        ResearcherServices["Researcher Services\n(Regime Queries, Risk Analytics, Backtests)"]
        AdminServices["Admin Services\n(System Configuration, Audit Log Access)"]
        PydanticSanitizer["Schema Validation & Input Sanitization\n(SQL / Command Injection Prevention)"]
    end

    subgraph Zone3["Isolated Internal Tier: Asynchronous Processing"]
        QueueBroker[("Redis Task Queue\n(Internal Subnet Only)")]
        WorkerProcesses["Celery Worker Processes\n(Non-Root Execution, No Public Port)"]
    end

    subgraph Zone4["Secure Persistence Tier: Data at Rest"]
        DatabaseEngine[("PostgreSQL + TimescaleDB\n(Encrypted at Rest, Strictly Internal Network)")]
    end

    subgraph Zone5["Outbound Egress Tier"]
        EgressController["Egress Adapter Controller\n(Isolated Outbound HTTPS Calls)"]
        ExtVendors["External Market Data & AI APIs"]
    end

    ExternalTraffic --> TLS
    TLS --> RateLimiter
    RateLimiter --> APIGateway

    APIGateway --> AuthModule
    AuthModule -- Unauthenticated (Public) --> PublicEndpoints
    AuthModule -- Valid Credentials --> RBAC

    RBAC -- Role: Researcher --> ResearcherServices
    RBAC -- Role: Administrator --> AdminServices
    
    ResearcherServices --> PydanticSanitizer
    AdminServices --> PydanticSanitizer

    PydanticSanitizer -->|Enqueue Jobs| QueueBroker
    QueueBroker --> WorkerProcesses

    PydanticSanitizer -->|Direct Query Pool| DatabaseEngine
    WorkerProcesses -->|Batch Persistence| DatabaseEngine

    WorkerProcesses --> EgressController
    APIGateway --> EgressController
    EgressController -->|Encrypted HTTPS Outbound| ExtVendors
```
